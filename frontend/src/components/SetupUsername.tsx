import { useState } from "react";
import { motion } from "framer-motion";
import { setMinecraftUsername } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function SetupUsername() {
  const { setUser } = useAuth();
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!/^[a-zA-Z0-9_]{3,16}$/.test(username)) {
      setError("Must be 3-16 characters, letters/numbers/underscores only");
      return;
    }

    setLoading(true);
    try {
      const updated = await setMinecraftUsername(username);
      setUser(updated);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-space-dark p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md rounded-xl border border-gold/20 bg-space-gray p-8"
      >
        <h2 className="font-serif text-2xl text-gold-light">
          Set Your Minecraft Username
        </h2>
        <p className="mt-2 font-mono text-sm text-white/40">
          Required before you can manage mods, vote, or play on the server.
          This will automatically whitelist you.
        </p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="block font-mono text-xs text-white/60 mb-1.5">
              Java Edition Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-space-dark px-4 py-2.5 font-mono text-sm text-white placeholder:text-white/20 focus:border-gold/40 focus:outline-none focus:ring-1 focus:ring-gold/20"
              placeholder="Steve"
              maxLength={16}
              autoFocus
            />
          </div>

          {error && (
            <p className="font-mono text-xs text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !username}
            className="w-full rounded-lg bg-gold/20 py-2.5 font-mono text-sm text-gold transition hover:bg-gold/30 disabled:opacity-40"
          >
            {loading ? "Setting up..." : "Continue"}
          </button>
        </form>
      </motion.div>
    </div>
  );
}
