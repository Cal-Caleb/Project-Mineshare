import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { getServerStatus, getUptimeStats } from "../lib/api";
import { useSSE } from "../hooks/useSSE";
import type { ServerStatus, UptimeStats } from "../lib/types";

const card =
  "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur p-6";

export default function ServerStatusPage() {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [uptime, setUptime] = useState<UptimeStats | null>(null);
  const [days, setDays] = useState(30);

  const fetchData = useCallback(() => {
    getServerStatus().then(setStatus).catch(() => {});
    getUptimeStats(days).then(setUptime).catch(() => {});
  }, [days]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useSSE(fetchData, ["server_status", "server_update"]);

  const fade = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
  };

  return (
    <motion.div {...fade} className="space-y-6">
      <h1 className="font-serif text-3xl text-gold-light">Server Status</h1>

      {/* Quick stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Status"
          value={status ? (status.online ? "Online" : "Offline") : "..."}
          tone={status?.online ? "good" : "bad"}
        />
        <StatCard
          label="Players"
          value={String(status?.player_count ?? "...")}
          subtitle={status?.players?.join(", ")}
        />
        <StatCard
          label={`${days}d Uptime`}
          value={uptime ? `${uptime.uptime_pct}%` : "..."}
          tone={
            uptime
              ? uptime.uptime_pct >= 95
                ? "good"
                : uptime.uptime_pct >= 80
                ? "accent"
                : "bad"
              : undefined
          }
        />
        <StatCard
          label="Peak Players"
          value={uptime ? String(uptime.peak_players) : "..."}
        />
        <StatCard
          label="World Size"
          value={
            uptime?.world_size_mb != null
              ? uptime.world_size_mb >= 1024
                ? `${(uptime.world_size_mb / 1024).toFixed(1)} GB`
                : `${Math.round(uptime.world_size_mb)} MB`
              : "—"
          }
        />
      </div>

      {/* Time range selector */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-white/40">Time range:</span>
        {[7, 14, 30, 60, 90].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1 rounded font-mono text-xs transition ${
              days === d
                ? "bg-gold/20 text-gold"
                : "text-white/40 hover:text-white/70"
            }`}
          >
            {d}d
          </button>
        ))}
      </div>

      {/* Uptime bar */}
      {uptime && <UptimeBar buckets={uptime.buckets} label={`${days}-Day Uptime`} />}

      {/* Player count graph */}
      {uptime && <PlayerGraph buckets={uptime.buckets} days={days} />}

      {/* Daily breakdown */}
      {uptime && <DailyBreakdown buckets={uptime.buckets} />}

      {/* Online players */}
      {status?.online && status.players.length > 0 && (
        <div className={card}>
          <h2 className="font-serif text-lg text-gold-light mb-3">
            Online Players ({status.players.length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {status.players.map((p) => (
              <span
                key={p}
                className="rounded-lg bg-emerald-500/10 px-3 py-1.5 font-mono text-sm text-emerald-300 ring-1 ring-emerald-500/20"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}
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

function UptimeBar({
  buckets,
  label,
}: {
  buckets: { online: boolean | null }[];
  label: string;
}) {
  // Group buckets into visual blocks (max ~500 blocks for display)
  const blockCount = Math.min(buckets.length, 500);
  const bucketsPer = Math.max(1, Math.floor(buckets.length / blockCount));

  const blocks = useMemo(() => {
    const result: ("online" | "offline" | "nodata")[] = [];
    for (let i = 0; i < buckets.length; i += bucketsPer) {
      const slice = buckets.slice(i, i + bucketsPer);
      const hasOnline = slice.some((b) => b.online === true);
      const hasOffline = slice.some((b) => b.online === false);
      const hasData = slice.some((b) => b.online !== null);
      if (!hasData) result.push("nodata");
      else if (hasOnline && !hasOffline) result.push("online");
      else if (hasOffline && !hasOnline) result.push("offline");
      else result.push(hasOnline ? "online" : "offline");
    }
    return result;
  }, [buckets, bucketsPer]);

  return (
    <div className={card}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-serif text-lg text-gold-light">{label}</h2>
        <div className="flex items-center gap-4 font-mono text-[10px] text-white/30">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-emerald-500" />
            Online
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-red-500" />
            Offline
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-white/10" />
            No data
          </span>
        </div>
      </div>
      <div className="flex h-6 w-full overflow-hidden rounded-md">
        {blocks.map((b, i) => (
          <div
            key={i}
            className={`flex-1 min-w-[1px] ${
              b === "online"
                ? "bg-emerald-500"
                : b === "offline"
                ? "bg-red-500"
                : "bg-white/5"
            }`}
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-white/20">
        <span>{label.split(" ")[0]} ago</span>
        <span>now</span>
      </div>
    </div>
  );
}

function PlayerGraph({
  buckets,
  days,
}: {
  buckets: { player_count: number; online: boolean | null }[];
  days: number;
}) {
  const maxPlayers = useMemo(
    () => Math.max(1, ...buckets.map((b) => b.player_count)),
    [buckets]
  );

  // Downsample to ~200 points for SVG
  const sampleCount = Math.min(buckets.length, 200);
  const step = Math.max(1, Math.floor(buckets.length / sampleCount));

  const points = useMemo(() => {
    const pts: { x: number; y: number; count: number }[] = [];
    for (let i = 0; i < buckets.length; i += step) {
      const slice = buckets.slice(i, i + step);
      const maxInSlice = Math.max(...slice.map((b) => b.player_count));
      const x = i / buckets.length;
      const y = 1 - maxInSlice / maxPlayers;
      pts.push({ x, y, count: maxInSlice });
    }
    return pts;
  }, [buckets, step, maxPlayers]);

  const w = 1000;
  const h = 200;
  const pad = { top: 10, bottom: 20, left: 0, right: 0 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const linePath = points
    .map(
      (p, i) =>
        `${i === 0 ? "M" : "L"} ${pad.left + p.x * plotW} ${
          pad.top + p.y * plotH
        }`
    )
    .join(" ");

  const areaPath =
    linePath +
    ` L ${pad.left + plotW} ${pad.top + plotH} L ${pad.left} ${
      pad.top + plotH
    } Z`;

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((frac) => ({
    y: pad.top + plotH * (1 - frac),
    label: Math.round(maxPlayers * frac),
  }));

  return (
    <div className={card}>
      <h2 className="font-serif text-lg text-gold-light mb-3">
        Player Count ({days} Days)
      </h2>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
        {/* Grid */}
        {yTicks.map((t) => (
          <g key={t.label}>
            <line
              x1={pad.left}
              y1={t.y}
              x2={pad.left + plotW}
              y2={t.y}
              stroke="rgba(255,255,255,0.05)"
              strokeWidth={1}
            />
          </g>
        ))}
        {/* Area fill */}
        <path d={areaPath} fill="rgba(192,152,80,0.1)" />
        {/* Line */}
        <path d={linePath} fill="none" stroke="#d4b06d" strokeWidth={2} />
      </svg>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-white/20">
        <span>{days}d ago</span>
        <span>Peak: {maxPlayers}</span>
        <span>now</span>
      </div>
    </div>
  );
}

function DailyBreakdown({
  buckets,
}: {
  buckets: { online: boolean | null; player_count: number }[];
}) {
  const dailyStats = useMemo(() => {
    const bpd = 144; // 10-min buckets per day
    const n = buckets.length;
    const daysAvailable = Math.min(14, Math.max(1, Math.floor(n / bpd)));
    const stats: {
      label: string;
      uptimePct: number;
      peak: number;
      avg: number;
    }[] = [];

    for (let d = 0; d < daysAvailable; d++) {
      const startIdx = n - (daysAvailable - d) * bpd;
      const endIdx = startIdx + bpd;
      const slice = buckets.slice(Math.max(0, startIdx), Math.min(n, endIdx));

      const known = slice.filter((b) => b.online !== null);
      const up = known.filter((b) => b.online).length;
      const pct = known.length > 0 ? (100 * up) / known.length : 0;
      const peak = Math.max(0, ...slice.map((b) => b.player_count));
      const onlineCounts = slice
        .filter((b) => b.online)
        .map((b) => b.player_count);
      const avg =
        onlineCounts.length > 0
          ? onlineCounts.reduce((a, b) => a + b, 0) / onlineCounts.length
          : 0;

      // Label: days ago
      const daysAgo = daysAvailable - d - 1;
      const label =
        daysAgo === 0 ? "Today" : daysAgo === 1 ? "Yesterday" : `${daysAgo}d ago`;

      stats.push({ label, uptimePct: Math.round(pct * 10) / 10, peak, avg: Math.round(avg * 10) / 10 });
    }
    return stats;
  }, [buckets]);

  if (dailyStats.length === 0) return null;

  return (
    <div className={card}>
      <h2 className="font-serif text-lg text-gold-light mb-3">
        Daily Breakdown
      </h2>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-7">
        {dailyStats.slice(-7).map((d) => (
          <div
            key={d.label}
            className="rounded-lg border border-white/5 bg-space-dark/40 p-3 text-center"
          >
            <p className="font-mono text-[10px] text-white/30 mb-1">
              {d.label}
            </p>
            <div
              className={`h-2 rounded-full mb-2 ${
                d.uptimePct >= 99
                  ? "bg-emerald-500"
                  : d.uptimePct >= 90
                  ? "bg-amber-500"
                  : "bg-red-500"
              }`}
            />
            <p className="font-mono text-sm text-white/70">
              {d.uptimePct}%
            </p>
            <p className="font-mono text-[10px] text-white/30">
              peak: {d.peak}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
