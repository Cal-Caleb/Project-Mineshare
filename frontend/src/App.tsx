import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Starfield from "./components/Starfield";
import Navbar from "./components/Navbar";
import LoginScreen from "./components/LoginScreen";
import SetupUsername from "./components/SetupUsername";
import AuthCallback from "./components/AuthCallback";
import Dashboard from "./components/Dashboard";
import ModCatalogue from "./components/ModCatalogue";
import AddMod from "./components/AddMod";
import ActiveVotes from "./components/ActiveVotes";
import AuditHistory from "./components/AuditHistory";
import AdminPanel from "./components/AdminPanel";
import ServerStatusPage from "./components/ServerStatusPage";
import ModUpdatesPage from "./components/ModUpdatesPage";

function AppRoutes() {
  const { user, loading, needsUsername } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-space-dark">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-gold border-t-transparent" />
          <p className="mt-4 font-mono text-sm text-white/40">
            Loading MineShare...
          </p>
        </div>
      </div>
    );
  }

  if (!user) return <LoginScreen />;
  if (needsUsername) return <SetupUsername />;

  return (
    <div className="relative min-h-screen bg-space-dark text-white">
      <Starfield />
      <div className="relative z-10">
        <Navbar />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/status" element={<ServerStatusPage />} />
              <Route path="/mods" element={<ModCatalogue />} />
              <Route path="/add-mod" element={<AddMod />} />
              <Route path="/votes" element={<ActiveVotes />} />
              <Route path="/updates" element={<ModUpdatesPage />} />
              <Route path="/audit" element={<AuditHistory />} />
              <Route path="/admin" element={<AdminPanel />} />
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="*" element={<AppRoutes />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
