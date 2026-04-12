import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { downloadModpack, listMods, removeMod, uploadModUpdate } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useSSE } from "../hooks/useSSE";
import type { Mod } from "../lib/types";

const card = "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur";

export default function ModCatalogue() {
  const [mods, setMods] = useState<Mod[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "active" | "pending_vote" | "removed">("all");
  const { user, isAdmin } = useAuth();

  const fetchMods = useCallback(() => {
    const status = filter === "all" ? undefined : filter;
    listMods(status)
      .then(setMods)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => { fetchMods(); }, [fetchMods]);
  useSSE(fetchMods, ["mod_added", "mod_removed", "mod_updated", "vote_resolved"]);

  const filtered = mods.filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      (m.author ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const handleRemove = async (mod: Mod, force: boolean) => {
    if (!confirm(`Remove "${mod.name}"${force ? " immediately" : " (starts a vote)"}?`)) return;
    try {
      await removeMod(mod.id, force);
      fetchMods();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const updateInputRefs = useRef<Record<number, HTMLInputElement | null>>({});
  const [updatingMod, setUpdatingMod] = useState<number | null>(null);

  const handleUpdateClick = (modId: number) => {
    updateInputRefs.current[modId]?.click();
  };

  const handleUpdateFile = async (mod: Mod, file: File | null) => {
    if (!file) return;
    if (!confirm(`Submit update "${file.name}" for "${mod.name}"? An admin will need to approve it.`)) return;
    setUpdatingMod(mod.id);
    try {
      await uploadModUpdate(mod.id, file);
      alert("Update submitted for admin approval.");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUpdatingMod(null);
      if (updateInputRefs.current[mod.id]) {
        updateInputRefs.current[mod.id]!.value = "";
      }
    }
  };

  const statusColor: Record<string, string> = {
    active: "bg-emerald-500/20 text-emerald-300",
    pending_vote: "bg-amber-500/20 text-amber-300",
    pending_approval: "bg-orange-500/20 text-orange-300",
    removed: "bg-red-500/20 text-red-300",
  };

  const fade = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
  };

  return (
    <motion.div {...fade} className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <h1 className="font-serif text-3xl text-gold-light">Mod Catalogue</h1>
          <button
            onClick={() => downloadModpack()}
            className="rounded-lg border border-gold/20 px-4 py-1.5 font-mono text-xs text-gold/70 transition hover:bg-gold/10 hover:text-gold"
            title="Download mod list as ZIP (JSON + TXT + HTML)"
          >
            <span className="flex items-center gap-1.5">
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export Modpack
            </span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* Filter tabs */}
          <div className="flex rounded-lg border border-white/10 overflow-hidden">
            {(["all", "active", "pending_vote", "removed"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 font-mono text-xs transition ${
                  filter === f
                    ? "bg-gold/20 text-gold"
                    : "text-white/40 hover:text-white/70"
                }`}
              >
                {f.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-48 rounded-lg border border-white/10 bg-space-dark px-3 py-1.5 font-mono text-sm text-white placeholder:text-white/20 focus:border-gold/30 focus:outline-none"
            placeholder="Search..."
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-gold border-t-transparent" />
        </div>
      ) : filtered.length === 0 ? (
        <div className={`${card} p-12 text-center`}>
          <p className="font-mono text-white/30">No mods found</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((mod, i) => (
            <motion.div
              key={mod.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className={`${card} p-5 group hover:border-gold/20 transition-colors`}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-serif text-lg text-white">{mod.name}</h3>
                <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${statusColor[mod.status] ?? ""}`}>
                  {mod.status.replace("_", " ")}
                </span>
              </div>

              {mod.author && (
                <p className="font-mono text-xs text-white/30">by {mod.author}</p>
              )}

              <div className="mt-3 flex items-center justify-between font-mono text-xs text-white/40">
                <span>{mod.current_version ?? "—"}</span>
                <span className="capitalize">{mod.source}</span>
              </div>

              {mod.download_count > 0 && (
                <p className="mt-1 font-mono text-[10px] text-white/20">
                  {mod.download_count.toLocaleString()} downloads
                </p>
              )}

              {/* Actions */}
              {mod.status === "active" && user && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {mod.source === "upload" &&
                    (mod.added_by?.id === user.id || isAdmin) && (
                      <>
                        <input
                          ref={(el) => {
                            updateInputRefs.current[mod.id] = el;
                          }}
                          type="file"
                          accept=".jar"
                          className="hidden"
                          onChange={(e) =>
                            handleUpdateFile(mod, e.target.files?.[0] ?? null)
                          }
                        />
                        <button
                          onClick={() => handleUpdateClick(mod.id)}
                          disabled={updatingMod === mod.id}
                          className="flex-1 rounded border border-blue-500/20 py-1 font-mono text-xs text-blue-300 hover:bg-blue-500/10 transition disabled:opacity-40"
                        >
                          {updatingMod === mod.id ? "Uploading..." : "Upload Update"}
                        </button>
                      </>
                    )}
                  {(mod.added_by?.id === user.id || isAdmin) && (
                    <button
                      onClick={() => handleRemove(mod, false)}
                      className="flex-1 rounded border border-red-500/20 py-1 font-mono text-xs text-red-400 hover:bg-red-500/10 transition"
                    >
                      Vote Remove
                    </button>
                  )}
                  {isAdmin && (
                    <button
                      onClick={() => handleRemove(mod, true)}
                      className="flex-1 rounded border border-red-500/30 py-1 font-mono text-xs text-red-300 hover:bg-red-500/20 transition"
                    >
                      Force Remove
                    </button>
                  )}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
