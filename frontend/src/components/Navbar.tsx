import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/mods", label: "Mods" },
  { to: "/add-mod", label: "Add Mod" },
  { to: "/votes", label: "Votes" },
  { to: "/audit", label: "Audit" },
];

export default function Navbar() {
  const { pathname } = useLocation();
  const { user, isAdmin, logout } = useAuth();

  return (
    <nav className="sticky top-0 z-50 border-b border-gold/20 bg-space-dark/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <motion.div
            className="flex h-9 w-9 items-center justify-center rounded-full bg-gold font-serif text-lg font-bold text-space-dark"
            animate={{ y: [0, -4, 0] }}
            transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
          >
            M
          </motion.div>
          <span className="font-serif text-xl tracking-wide text-gold-light">
            MineShare
          </span>
        </Link>

        {/* Nav links */}
        <div className="hidden items-center gap-1 md:flex">
          {links.map((l) => {
            const active = pathname === l.to;
            return (
              <Link
                key={l.to}
                to={l.to}
                className={`relative px-3 py-1.5 text-sm font-mono transition-colors ${
                  active ? "text-gold" : "text-white/60 hover:text-white"
                }`}
              >
                {l.label}
                {active && (
                  <motion.div
                    layoutId="nav-underline"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </Link>
            );
          })}
          {isAdmin && (
            <Link
              to="/admin"
              className={`px-3 py-1.5 text-sm font-mono transition-colors ${
                pathname === "/admin"
                  ? "text-gold"
                  : "text-white/60 hover:text-white"
              }`}
            >
              Admin
            </Link>
          )}
        </div>

        {/* User area */}
        <div className="flex items-center gap-3">
          {user && (
            <>
              <span className="hidden text-sm text-white/50 font-mono sm:block">
                {user.mc_username ?? user.discord_username}
              </span>
              <button
                onClick={logout}
                className="rounded border border-white/10 px-3 py-1 text-xs font-mono text-white/50 transition hover:border-gold/40 hover:text-gold"
              >
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
