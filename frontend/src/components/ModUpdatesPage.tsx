import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getModUpdates } from "../lib/api";
import { useSSE } from "../hooks/useSSE";
import type { ModUpdate } from "../lib/types";

const card =
  "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur p-6";

export default function ModUpdatesPage() {
  const [updates, setUpdates] = useState<ModUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const fetchUpdates = useCallback(() => {
    getModUpdates(100)
      .then(setUpdates)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchUpdates();
  }, [fetchUpdates]);

  useSSE(fetchUpdates, ["mod_updated"]);

  const fade = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
  };

  return (
    <motion.div {...fade} className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-3xl text-gold-light">Mod Updates</h1>
        <span className="font-mono text-xs text-white/30">
          {updates.length} updates recorded
        </span>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-gold border-t-transparent" />
        </div>
      ) : updates.length === 0 ? (
        <div className={`${card} text-center py-12`}>
          <p className="font-mono text-white/30">
            No mod updates yet. Updates will appear here when CurseForge mods
            are updated during the server update cycle.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {updates.map((u, i) => (
            <motion.div
              key={u.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.02 }}
            >
              <UpdateCard
                update={u}
                isExpanded={expandedId === u.id}
                onToggle={() =>
                  setExpandedId(expandedId === u.id ? null : u.id)
                }
              />
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

function UpdateCard({
  update,
  isExpanded,
  onToggle,
}: {
  update: ModUpdate;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const date = new Date(update.created_at);

  return (
    <div
      className={`${card} transition-colors hover:border-blue-500/20 cursor-pointer`}
      onClick={onToggle}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2.5 py-0.5 font-mono text-[10px] text-blue-400 ring-1 ring-blue-500/20">
              UPDATE
            </span>
            <h3 className="font-serif text-lg text-white truncate">
              {update.mod_name}
            </h3>
          </div>

          <div className="flex items-center gap-2 font-mono text-sm">
            {update.old_version && (
              <span className="text-red-400/70 line-through truncate max-w-[200px]">
                {update.old_version}
              </span>
            )}
            <span className="text-white/30">→</span>
            {update.new_version && (
              <span className="text-emerald-400 truncate max-w-[200px]">
                {update.new_version}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {update.source_url && (
            <a
              href={update.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded border border-white/10 px-3 py-1 font-mono text-xs text-white/50 hover:border-gold/40 hover:text-gold transition"
              onClick={(e) => e.stopPropagation()}
            >
              CurseForge
            </a>
          )}
          <span className="font-mono text-xs text-white/20">
            {date.toLocaleDateString()}
          </span>
          <svg
            className={`h-4 w-4 text-white/30 transition-transform ${
              isExpanded ? "rotate-180" : ""
            }`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && update.changelog && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-4 rounded-lg border border-white/5 bg-space-dark/50 p-4">
              <h4 className="font-mono text-xs text-white/40 uppercase tracking-wider mb-2">
                Changelog
              </h4>
              <div className="font-mono text-xs text-white/60 whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto">
                {update.changelog}
              </div>
            </div>
          </motion.div>
        )}
        {isExpanded && !update.changelog && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <p className="mt-4 font-mono text-xs text-white/30 italic">
              No changelog available for this update.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
