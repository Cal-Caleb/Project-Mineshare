import { motion } from "framer-motion";
import { getLoginUrl } from "../lib/api";
import Starfield from "./Starfield";

export default function LoginScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-space-dark">
      <Starfield />
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="relative z-10 flex flex-col items-center gap-8 text-center"
      >
        <motion.div
          className="flex h-24 w-24 items-center justify-center rounded-full border-2 border-gold/40 bg-space-dark font-serif text-5xl font-bold text-gold"
          animate={{ y: [0, -8, 0] }}
          transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
        >
          M
        </motion.div>

        <div>
          <h1 className="font-serif text-4xl tracking-wide text-gold-light">
            MineShare
          </h1>
          <p className="mt-2 font-mono text-sm text-white/40">
            Collaborative Modded Minecraft Server Management
          </p>
        </div>

        <a
          href={getLoginUrl()}
          className="group flex items-center gap-2 rounded-lg border border-gold/30 bg-gold/10 px-6 py-3 font-mono text-sm text-gold transition hover:bg-gold/20 hover:border-gold/60"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current">
            <path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03z" />
          </svg>
          Sign in with Discord
        </a>
      </motion.div>
    </div>
  );
}
