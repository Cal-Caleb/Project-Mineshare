import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  castBallot,
  getAuditLog,
  getServerStatus,
  getUptimeStats,
  listActiveVotes,
  listMods,
  listPendingUploads,
} from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useSSE } from "../hooks/useSSE";
import type {
  AuditEntry,
  Mod,
  ServerStatus,
  Upload,
  UptimeStats,
  Vote,
} from "../lib/types";

const card =
  "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur p-6";

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [uptime, setUptime] = useState<UptimeStats | null>(null);
  const [mods, setMods] = useState<Mod[]>([]);
  const [votes, setVotes] = useState<Vote[]>([]);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [recent, setRecent] = useState<AuditEntry[]>([]);

  const fetchAll = useCallback(() => {
    getServerStatus().then(setStatus).catch(() => {});
    getUptimeStats(30).then(setUptime).catch(() => {});
    listMods("active").then(setMods).catch(() => {});
    listActiveVotes().then(setVotes).catch(() => {});
    getAuditLog(8).then(setRecent).catch(() => {});
    if (isAdmin) {
      listPendingUploads().then(setUploads).catch(() => {});
    }
  }, [isAdmin]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useSSE(fetchAll, [
    "server_status",
    "server_update",
    "mod_added",
    "mod_removed",
    "vote_created",
    "vote_cast",
    "vote_resolved",
    "upload_pending",
    "upload_resolved",
  ]);

  const fade = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4 },
  };

  const needsAttention = votes.length > 0 || (isAdmin && uploads.length > 0);

  return (
    <motion.div {...fade} className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="font-serif text-3xl text-gold-light">Dashboard</h1>
        <p className="font-mono text-xs text-white/30">
          Welcome back, {user?.mc_username ?? user?.discord_username}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Link to="/status">
          <StatCard
            label="Server"
            value={status ? (status.online ? "Online" : "Offline") : "..."}
            tone={status?.online ? "good" : "bad"}
          />
        </Link>
        <Link to="/status">
          <StatCard
            label="Players"
            value={String(status?.player_count ?? "...")}
            subtitle={status?.players?.join(", ")}
          />
        </Link>
        <StatCard label="Active Mods" value={String(mods.length)} />
        <StatCard
          label="30d Uptime"
          value={uptime ? `${uptime.uptime_pct}%` : "..."}
          tone={uptime ? (uptime.uptime_pct >= 95 ? "good" : uptime.uptime_pct >= 80 ? "accent" : "bad") : undefined}
        />
        <StatCard
          label="Open Votes"
          value={String(votes.length)}
          tone={votes.length > 0 ? "accent" : undefined}
        />
      </div>

      {/* Action needed */}
      {needsAttention && (
        <div className={card}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-serif text-lg text-gold-light">
              Needs Your Attention
            </h2>
            <span className="font-mono text-[10px] uppercase text-gold/70">
              Live
            </span>
          </div>

          <div className="space-y-3">
            {votes.map((v) => (
              <VoteRow key={v.id} vote={v} onAction={fetchAll} />
            ))}

            {isAdmin &&
              uploads.map((u) => (
                <div
                  key={`u-${u.id}`}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/5 bg-space-dark/30 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="font-mono text-sm text-white/80 truncate">
                      📦 {u.original_filename}
                    </p>
                    <p className="font-mono text-[10px] text-white/30">
                      {u.mod_id != null
                        ? `Update for mod #${u.mod_id}`
                        : "New upload · needs approval"}
                    </p>
                  </div>
                  <Link
                    to="/admin"
                    className="rounded border border-gold/30 px-3 py-1 font-mono text-xs text-gold hover:bg-gold/10"
                  >
                    Review
                  </Link>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Recent activity */}
      <div className={card}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-serif text-lg text-gold-light">Recent Activity</h2>
          <Link
            to="/audit"
            className="font-mono text-xs text-white/40 hover:text-gold"
          >
            View all →
          </Link>
        </div>
        {recent.length === 0 ? (
          <p className="font-mono text-sm text-white/30">No activity yet</p>
        ) : (
          <div className="space-y-3">
            {recent.map((e) => (
              <div
                key={e.id}
                className="flex items-center justify-between border-b border-white/5 pb-2 last:border-0"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <SourceBadge source={e.source} />
                  <div className="min-w-0">
                    <p className="font-mono text-sm text-white/80 truncate">
                      {e.action.replace(/_/g, " ")}
                    </p>
                    {e.details && (
                      <p className="font-mono text-xs text-white/30 truncate">
                        {e.details}
                      </p>
                    )}
                  </div>
                </div>
                <span className="ml-3 hidden font-mono text-xs text-white/20 shrink-0 sm:inline">
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

function StatCard({
  label,
  value,
  subtitle,
  tone,
}: {
  label: string;
  value: string;
  subtitle?: string;
  tone?: "good" | "bad" | "accent";
}) {
  const colorClass =
    tone === "good"
      ? "text-emerald-400"
      : tone === "bad"
      ? "text-red-400"
      : tone === "accent"
      ? "text-gold"
      : "text-white";
  return (
    <div className={card}>
      <p className="font-mono text-xs text-white/40 uppercase tracking-wider">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-bold ${colorClass}`}>{value}</p>
      {subtitle && (
        <p className="mt-1 font-mono text-xs text-white/30 truncate">
          {subtitle}
        </p>
      )}
    </div>
  );
}

function VoteRow({ vote, onAction }: { vote: Vote; onAction: () => void }) {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const myBallot = vote.ballots.find((b) => b.user.id === user?.id);

  const cast = async (inFavor: boolean) => {
    if (busy) return;
    if (myBallot && myBallot.in_favor === inFavor) return;
    setBusy(true);
    try {
      await castBallot(vote.id, inFavor);
      onAction();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setBusy(false);
    }
  };

  const typeLabel = vote.vote_type === "add" ? "Add" : "Remove";
  const typeColor =
    vote.vote_type === "add" ? "text-emerald-300" : "text-red-300";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/5 bg-space-dark/30 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="font-mono text-sm text-white/80 truncate">
          <span className={`mr-1.5 font-bold ${typeColor}`}>{typeLabel}:</span>
          {vote.mod.name}
        </p>
        <p className="font-mono text-[10px] text-white/30">
          {vote.tally?.yes ?? 0} yes · {vote.tally?.no ?? 0} no · expires{" "}
          {new Date(vote.expires_at).toLocaleDateString()}
        </p>
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => cast(true)}
          disabled={busy}
          className={`rounded px-3 py-1 font-mono text-xs transition disabled:opacity-40 ${
            myBallot?.in_favor === true
              ? "bg-emerald-500/30 text-emerald-200 ring-1 ring-emerald-400/40"
              : "bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
          }`}
        >
          Yes
        </button>
        <button
          onClick={() => cast(false)}
          disabled={busy}
          className={`rounded px-3 py-1 font-mono text-xs transition disabled:opacity-40 ${
            myBallot?.in_favor === false
              ? "bg-red-500/30 text-red-200 ring-1 ring-red-400/40"
              : "bg-red-500/10 text-red-300 hover:bg-red-500/20"
          }`}
        >
          No
        </button>
      </div>
    </div>
  );
}

function SourceBadge({ source }: { source: string }) {
  const colors: Record<string, string> = {
    web: "bg-blue-500/20 text-blue-300",
    discord: "bg-indigo-500/20 text-indigo-300",
    system: "bg-emerald-500/20 text-emerald-300",
  };
  return (
    <span
      className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] uppercase ${
        colors[source] ?? "bg-white/10 text-white/40"
      }`}
    >
      {source}
    </span>
  );
}
