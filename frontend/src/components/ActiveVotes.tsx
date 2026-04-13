import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  listActiveVotes,
  castBallot,
  vetoVote,
  forcePassVote,
  getVoteHistory,
} from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useSSE } from "../hooks/useSSE";
import type { Vote } from "../lib/types";

const card = "rounded-xl border border-white/5 bg-space-gray/60 backdrop-blur p-5";

export default function ActiveVotes() {
  const [active, setActive] = useState<Vote[]>([]);
  const [history, setHistory] = useState<Vote[]>([]);
  const [loading, setLoading] = useState(true);
  const [showHistory, setShowHistory] = useState(false);

  const fetchVotes = useCallback(() => {
    listActiveVotes()
      .then(setActive)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchVotes(); }, [fetchVotes]);
  useSSE(fetchVotes, ["vote_created", "vote_cast", "vote_resolved"]);

  const loadHistory = () => {
    setShowHistory(true);
    getVoteHistory(20).then(setHistory).catch(() => {});
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-gold border-t-transparent" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-3xl text-gold-light">Active Votes</h1>
        {!showHistory && (
          <button
            onClick={loadHistory}
            className="font-mono text-xs text-white/30 hover:text-gold transition"
          >
            View history
          </button>
        )}
      </div>

      {active.length === 0 ? (
        <div className={`${card} text-center py-12`}>
          <p className="font-mono text-white/30">No active votes right now</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {active.map((vote, i) => (
            <VoteCard key={vote.id} vote={vote} index={i} onUpdate={fetchVotes} />
          ))}
        </div>
      )}

      {showHistory && history.length > 0 && (
        <div className="space-y-4">
          <h2 className="font-serif text-xl text-gold-light/70">Past Votes</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {history.map((vote, i) => (
              <VoteCard key={vote.id} vote={vote} index={i} readonly />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

function VoteCard({
  vote,
  index,
  readonly,
  onUpdate,
}: {
  vote: Vote;
  index: number;
  readonly?: boolean;
  onUpdate?: () => void;
}) {
  const { user, isAdmin } = useAuth();
  const [acting, setActing] = useState(false);

  const isPending = vote.status === "pending";
  const tally = vote.tally ?? { yes: 0, no: 0, total: 0 };
  const total = tally.yes + tally.no || 1;
  const yesPct = (tally.yes / total) * 100;
  const myBallot = vote.ballots.find((b) => b.user.id === user?.id);

  const timeLeft = isPending
    ? getTimeLeft(vote.expires_at)
    : null;

  const handleVote = async (inFavor: boolean) => {
    setActing(true);
    try {
      await castBallot(vote.id, inFavor);
      onUpdate?.();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActing(false);
    }
  };

  const handleVeto = async () => {
    if (!confirm("Veto this vote?")) return;
    setActing(true);
    try {
      await vetoVote(vote.id);
      onUpdate?.();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActing(false);
    }
  };

  const handleForcePass = async () => {
    if (!confirm("Force pass this vote?")) return;
    setActing(true);
    try {
      await forcePassVote(vote.id);
      onUpdate?.();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActing(false);
    }
  };

  const statusColors: Record<string, string> = {
    pending: "border-amber-500/30",
    approved: "border-emerald-500/30",
    rejected: "border-red-500/30",
    vetoed: "border-red-500/30",
    force_approved: "border-blue-500/30",
    expired: "border-white/10",
  };

  const statusBadge: Record<string, string> = {
    pending: "bg-amber-500/20 text-amber-300",
    approved: "bg-emerald-500/20 text-emerald-300",
    rejected: "bg-red-500/20 text-red-300",
    vetoed: "bg-red-500/20 text-red-300",
    force_approved: "bg-blue-500/20 text-blue-300",
    expired: "bg-white/10 text-white/40",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`rounded-xl border bg-space-gray/60 backdrop-blur p-5 ${statusColors[vote.status] ?? ""}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-serif text-lg text-white">{vote.mod.name}</h3>
          <p className={`font-mono text-xs ${vote.vote_type === "add" ? "text-emerald-400" : "text-red-400"}`}>
            {vote.vote_type === "add" ? "Add Mod" : "Remove Mod"}
          </p>
        </div>
        <span className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${statusBadge[vote.status] ?? ""}`}>
          {vote.status.replace("_", " ")}
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex justify-between font-mono text-xs text-white/40 mb-1">
          <span>Yes: {tally.yes}</span>
          <span>No: {tally.no}</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${yesPct}%` }}
          />
        </div>
        <p className="mt-1 font-mono text-[10px] text-white/20">
          {tally.total} {tally.total === 1 ? "vote" : "votes"} cast
        </p>
      </div>

      {/* Time left */}
      {timeLeft && (
        <p className="mb-3 font-mono text-xs text-white/30">
          Expires: {timeLeft}
        </p>
      )}

      {/* Voters */}
      {vote.ballots.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {vote.ballots.map((b) => (
            <span
              key={b.id}
              className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                b.in_favor
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-red-500/10 text-red-400"
              }`}
            >
              {b.user.discord_username}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      {isPending && !readonly && (
        <div className="flex flex-wrap gap-2 mt-4">
          <button
            onClick={() => handleVote(true)}
            disabled={acting || myBallot?.in_favor === true}
            className={`flex-1 rounded-lg py-1.5 font-mono text-xs transition disabled:opacity-40 ${
              myBallot?.in_favor === true
                ? "bg-emerald-500/40 text-emerald-200 ring-1 ring-emerald-400/50"
                : "bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
            }`}
          >
            {myBallot?.in_favor === true ? "Voted Yes" : "Vote Yes"}
          </button>
          <button
            onClick={() => handleVote(false)}
            disabled={acting || myBallot?.in_favor === false}
            className={`flex-1 rounded-lg py-1.5 font-mono text-xs transition disabled:opacity-40 ${
              myBallot?.in_favor === false
                ? "bg-red-500/40 text-red-200 ring-1 ring-red-400/50"
                : "bg-red-500/20 text-red-300 hover:bg-red-500/30"
            }`}
          >
            {myBallot?.in_favor === false ? "Voted No" : "Vote No"}
          </button>
          {isAdmin && (
            <>
              <button
                onClick={handleVeto}
                disabled={acting}
                className="flex-1 rounded-lg border border-red-500/20 py-1.5 font-mono text-[10px] text-red-400 transition hover:bg-red-500/10 disabled:opacity-40"
              >
                Veto
              </button>
              <button
                onClick={handleForcePass}
                disabled={acting}
                className="flex-1 rounded-lg border border-blue-500/20 py-1.5 font-mono text-[10px] text-blue-400 transition hover:bg-blue-500/10 disabled:opacity-40"
              >
                Force Pass
              </button>
            </>
          )}
        </div>
      )}
    </motion.div>
  );
}

function getTimeLeft(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now();
  if (diff <= 0) return "Expired";
  const hours = Math.floor(diff / 3600000);
  const mins = Math.floor((diff % 3600000) / 60000);
  return `${hours}h ${mins}m`;
}
