import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../context/AuthContext";

type NavLink = { to: string; label: string; adminOnly?: boolean };

const links: NavLink[] = [
  { to: "/", label: "Dashboard" },
  { to: "/status", label: "Status" },
  { to: "/mods", label: "Mods" },
  { to: "/add-mod", label: "Add Mod" },
  { to: "/votes", label: "Votes" },
  { to: "/updates", label: "Updates" },
  { to: "/audit", label: "Audit" },
  { to: "/admin", label: "Admin", adminOnly: true },
];

export default function Navbar() {
  const { pathname } = useLocation();
  const { user, isAdmin, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const visibleLinks = links.filter((l) => !l.adminOnly || isAdmin);

  return (
    <nav className="sticky top-0 z-50 border-b border-gold/20 bg-space-dark/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        {/* Logo */}
        <Link to="/" className="flex shrink-0 items-center gap-2.5 group">
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

        {/* Desktop nav */}
        <div className="hidden items-center gap-1 md:flex">
          {visibleLinks.map((l) => {
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
        </div>

        {/* User area + mobile toggle */}
        <div className="flex items-center gap-2 sm:gap-3">
          {user && (
            <span className="hidden text-sm text-white/50 font-mono sm:block">
              {user.mc_username ?? user.discord_username}
            </span>
          )}
          {user && (
            <button
              onClick={logout}
              className="hidden rounded border border-white/10 px-3 py-1 text-xs font-mono text-white/50 transition hover:border-gold/40 hover:text-gold md:block"
            >
              Logout
            </button>
          )}
          <button
            aria-label="Toggle menu"
            onClick={() => setMobileOpen((o) => !o)}
            className="flex h-9 w-9 items-center justify-center rounded border border-white/10 text-white/70 transition hover:border-gold/40 hover:text-gold md:hidden"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              {mobileOpen ? (
                <path d="M6 6l12 12M6 18L18 6" strokeLinecap="round" />
              ) : (
                <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="border-t border-white/5 bg-space-dark/95 md:hidden"
          >
            <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-3">
              {visibleLinks.map((l) => {
                const active = pathname === l.to;
                return (
                  <Link
                    key={l.to}
                    to={l.to}
                    className={`rounded px-3 py-2 font-mono text-sm ${
                      active
                        ? "bg-gold/10 text-gold"
                        : "text-white/70 hover:bg-white/5"
                    }`}
                  >
                    {l.label}
                  </Link>
                );
              })}
              {user && (
                <button
                  onClick={logout}
                  className="mt-1 rounded border border-white/10 px-3 py-2 text-left font-mono text-xs text-white/50 transition hover:border-gold/40 hover:text-gold"
                >
                  Logout ({user.mc_username ?? user.discord_username})
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}
