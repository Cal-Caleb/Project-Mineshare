import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getServerStatus, getAuditLog, listMods, listActiveVotes } from "../lib/api";
import { useSSE } from "../hooks/useSSE";
import type { AuditEntry, Mod, ServerStatus, Vote } from "../lib/types";

const card = "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur p-6";

export default function Dashboard() {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [mods, setMods] = useState<Mod[]>([]);
  const [votes, setVotes] = useState<Vote[]>([]);
  const [recent, setRecent] = useState<AuditEntry[]>([]);

  const fetchAll = useCallback(() => {
    getServerStatus().then(setStatus).catch(() => {});
    listMods("active").then(setMods).catch(() => {});
    listActiveVotes().then(setVotes).catch(() => {});
    getAuditLog(8).then(setRecent).catch(() => {});
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  useSSE(fetchAll, ["server_status", "server_update", "mod_added", "mod_removed", "vote_resolved"]);

  const fade = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4 },
  };

  return (
    <motion.div {...fade} className="space-y-6">
      <h1 className="font-serif text-3xl text-gold-light">Dashboard</h1>

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className={card}>
          <p className="font-mono text-xs text-white/40 uppercase tracking-wider">Server</p>
          <p className={`mt-1 text-2xl font-bold ${status?.online ? "text-emerald-400" : "text-red-400"}`}>
            {status ? (status.online ? "Online" : "Offline") : "..."}
          </p>
        </div>
        <div className={card}>
          <p className="font-mono text-xs text-white/40 uppercase tracking-wider">Players</p>
          <p className="mt-1 text-2xl font-bold text-white">
            {status?.player_count ?? "..."}
          </p>
          {status?.players && status.players.length > 0 && (
            <p className="mt-1 font-mono text-xs text-white/30 truncate">
              {status.players.join(", ")}
            </p>
          )}
        </div>
        <div className={card}>
          <p className="font-mono text-xs text-white/40 uppercase tracking-wider">Active Mods</p>
          <p className="mt-1 text-2xl font-bold text-white">{mods.length}</p>
        </div>
        <div className={card}>
          <p className="font-mono text-xs text-white/40 uppercase tracking-wider">Open Votes</p>
          <p className="mt-1 text-2xl font-bold text-gold">{votes.length}</p>
        </div>
      </div>

      {/* Recent activity */}
      <div className={card}>
        <h2 className="font-serif text-lg text-gold-light mb-4">Recent Activity</h2>
        {recent.length === 0 ? (
          <p className="font-mono text-sm text-white/30">No activity yet</p>
        ) : (
          <div className="space-y-3">
            {recent.map((e) => (
              <div
                key={e.id}
                className="flex items-center justify-between border-b border-white/5 pb-2 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <SourceBadge source={e.source} />
                  <div>
                    <p className="font-mono text-sm text-white/80">{e.action.replace(/_/g, " ")}</p>
                    {e.details && (
                      <p className="font-mono text-xs text-white/30">{e.details}</p>
                    )}
                  </div>
                </div>
                <span className="font-mono text-xs text-white/20 shrink-0">
                  {new Date(e.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function SourceBadge({ source }: { source: string }) {
  const colors: Record<string, string> = {
    web: "bg-blue-500/20 text-blue-300",
    discord: "bg-indigo-500/20 text-indigo-300",
    system: "bg-emerald-500/20 text-emerald-300",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase ${colors[source] ?? "bg-white/10 text-white/40"}`}>
      {source}
    </span>
  );
}
