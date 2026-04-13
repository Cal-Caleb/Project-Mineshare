import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getAuditLog } from "../lib/api";
import type { AuditEntry } from "../lib/types";

const PAGE_SIZE = 30;

export default function AuditHistory() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const fetch = useCallback(() => {
    setLoading(true);
    getAuditLog(PAGE_SIZE, offset)
      .then((data) => {
        setEntries(data);
        setHasMore(data.length === PAGE_SIZE);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [offset]);

  useEffect(() => { fetch(); }, [fetch]);

  const sourceColors: Record<string, string> = {
    web: "bg-blue-500/20 text-blue-300",
    discord: "bg-indigo-500/20 text-indigo-300",
    system: "bg-emerald-500/20 text-emerald-300",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <h1 className="font-serif text-3xl text-gold-light">Audit History</h1>

      <div className="rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-gold border-t-transparent" />
          </div>
        ) : entries.length === 0 ? (
          <div className="py-16 text-center">
            <p className="font-mono text-sm text-white/30">No audit entries</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="border-b border-white/5 text-left">
                  <th className="px-5 py-3 font-mono text-[10px] text-white/30 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-5 py-3 font-mono text-[10px] text-white/30 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-5 py-3 font-mono text-[10px] text-white/30 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-5 py-3 font-mono text-[10px] text-white/30 uppercase tracking-wider">
                    Details
                  </th>
                  <th className="px-5 py-3 font-mono text-[10px] text-white/30 uppercase tracking-wider">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, i) => (
                  <motion.tr
                    key={e.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.02 }}
                    className="border-b border-white/[0.03] hover:bg-white/[0.02] transition"
                  >
                    <td className="px-5 py-3 font-mono text-xs text-white/30 whitespace-nowrap">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-white/60">
                      {e.user?.discord_username ?? "System"}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-white/70">
                      {e.action.replace(/_/g, " ")}
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-white/40 max-w-xs truncate">
                      {e.details}
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                          sourceColors[e.source] ?? "bg-white/10 text-white/40"
                        }`}
                      >
                        {e.source}
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-center gap-3">
        <button
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          disabled={offset === 0}
          className="rounded border border-white/10 px-4 py-1.5 font-mono text-xs text-white/40 transition hover:border-gold/30 hover:text-gold disabled:opacity-20"
        >
          Previous
        </button>
        <button
          onClick={() => setOffset(offset + PAGE_SIZE)}
          disabled={!hasMore}
          className="rounded border border-white/10 px-4 py-1.5 font-mono text-xs text-white/40 transition hover:border-gold/30 hover:text-gold disabled:opacity-20"
        >
          Next
        </button>
      </div>
    </motion.div>
  );
}
