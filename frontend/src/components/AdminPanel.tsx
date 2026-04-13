import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  triggerUpdate,
  restartServer,
  createBackup,
  getServerEvents,
  listPendingUploads,
  approveUpload,
  rejectUpload,
  downloadUpload,
} from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useSSE } from "../hooks/useSSE";
import type { ServerEvent, Upload } from "../lib/types";
import { Navigate } from "react-router-dom";

const card = "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur p-6";

export default function AdminPanel() {
  const { isAdmin } = useAuth();

  if (!isAdmin) return <Navigate to="/" replace />;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <h1 className="font-serif text-3xl text-gold-light">Admin Panel</h1>

      <div className="grid gap-6 lg:grid-cols-2">
        <ServerControls />
        <PendingUploads />
      </div>

      <ServerHistory />
    </motion.div>
  );
}

function ServerControls() {
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const run = async (label: string, fn: () => Promise<any>) => {
    if (!confirm(`${label}?`)) return;
    setBusy(label);
    setMsg("");
    try {
      const result = await fn();
      setMsg(`${label}: ${result.status ?? "done"}`);
    } catch (err: any) {
      setMsg(`${label} failed: ${err.message}`);
    } finally {
      setBusy(null);
    }
  };

  const actions = [
    { label: "Manual Update Check", fn: triggerUpdate, color: "blue" },
    { label: "Restart Server", fn: restartServer, color: "purple" },
    { label: "Backup World", fn: createBackup, color: "amber" },
  ];

  const colorMap: Record<string, string> = {
    blue: "border-blue-500/20 text-blue-300 hover:bg-blue-500/10",
    purple: "border-purple-500/20 text-purple-300 hover:bg-purple-500/10",
    amber: "border-amber-500/20 text-amber-300 hover:bg-amber-500/10",
  };

  return (
    <div className={card}>
      <h2 className="font-serif text-lg text-gold-light mb-4">Server Controls</h2>
      <div className="grid grid-cols-1 gap-3">
        {actions.map((a) => (
          <button
            key={a.label}
            onClick={() => run(a.label, a.fn)}
            disabled={!!busy}
            className={`rounded-lg border py-3 font-mono text-sm transition disabled:opacity-40 ${colorMap[a.color]}`}
          >
            {busy === a.label ? `${a.label}...` : a.label}
          </button>
        ))}
      </div>
      {msg && (
        <p className="mt-3 font-mono text-xs text-white/40">{msg}</p>
      )}
    </div>
  );
}

function PendingUploads() {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [acting, setActing] = useState<number | null>(null);

  const fetch = useCallback(() => {
    listPendingUploads().then(setUploads).catch(() => {});
  }, []);

  useEffect(() => { fetch(); }, [fetch]);
  useSSE(fetch, ["upload_pending", "upload_resolved"]);

  const handleApprove = async (u: Upload) => {
    let name: string | undefined;
    if (u.mod_id == null) {
      const entered = prompt("Enter a display name for this mod:");
      if (!entered) return;
      name = entered;
    } else {
      if (!confirm("Approve this mod update? It will replace the existing file — no vote required.")) return;
    }
    setActing(u.id);
    try {
      await approveUpload(u.id, name);
      fetch();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActing(null);
    }
  };

  const handleReject = async (id: number) => {
    const reason = prompt("Rejection reason (optional):") ?? "";
    setActing(id);
    try {
      await rejectUpload(id, reason);
      fetch();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActing(null);
    }
  };

  return (
    <div className={card}>
      <h2 className="font-serif text-lg text-gold-light mb-4">
        Pending Uploads ({uploads.length})
      </h2>
      {uploads.length === 0 ? (
        <p className="font-mono text-xs text-white/30">No pending uploads</p>
      ) : (
        <div className="space-y-3">
          {uploads.map((u) => (
            <div
              key={u.id}
              className="rounded-lg border border-white/5 bg-space-dark/30 p-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-sm text-white/70 truncate">
                  {u.original_filename}
                </span>
                <span className="font-mono text-[10px] text-white/30">
                  {(u.file_size / 1024 / 1024).toFixed(1)} MB
                </span>
              </div>
              <p className="font-mono text-[10px] text-white/20 mb-2">
                {u.mod_id != null ? (
                  <span className="text-amber-300/70">UPDATE for mod #{u.mod_id}</span>
                ) : (
                  <span className="text-emerald-300/70">NEW MOD</span>
                )}{" "}
                | {u.status} | {new Date(u.created_at).toLocaleDateString()}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => downloadUpload(u.id, u.original_filename)}
                  className="flex-1 rounded bg-blue-500/20 py-1 font-mono text-xs text-blue-300 transition hover:bg-blue-500/30"
                >
                  Download
                </button>
                <button
                  onClick={() => handleApprove(u)}
                  disabled={acting === u.id}
                  className="flex-1 rounded bg-emerald-500/20 py-1 font-mono text-xs text-emerald-300 transition hover:bg-emerald-500/30 disabled:opacity-40"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleReject(u.id)}
                  disabled={acting === u.id}
                  className="flex-1 rounded bg-red-500/20 py-1 font-mono text-xs text-red-300 transition hover:bg-red-500/30 disabled:opacity-40"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ServerHistory() {
  const [events, setEvents] = useState<ServerEvent[]>([]);

  useEffect(() => {
    getServerEvents(15).then(setEvents).catch(() => {});
  }, []);

  const statusColors: Record<string, string> = {
    started: "text-amber-300",
    success: "text-emerald-300",
    failed: "text-red-300",
  };

  return (
    <div className={card}>
      <h2 className="font-serif text-lg text-gold-light mb-4">Server Events</h2>
      {events.length === 0 ? (
        <p className="font-mono text-xs text-white/30">No events yet</p>
      ) : (
        <div className="space-y-2">
          {events.map((e) => (
            <div
              key={e.id}
              className="flex items-center justify-between border-b border-white/[0.03] pb-2 last:border-0"
            >
              <div>
                <span className="font-mono text-xs text-white/60">
                  {e.event_type.replace(/_/g, " ")}
                </span>
                <span className={`ml-2 font-mono text-xs ${statusColors[e.status] ?? "text-white/40"}`}>
                  {e.status}
                </span>
              </div>
              <span className="font-mono text-[10px] text-white/20">
                {new Date(e.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
