import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getMe } from "../lib/api";
import type { User } from "../lib/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  isAdmin: boolean;
  needsUsername: boolean;
  setUser: (u: User | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  isAdmin: false,
  needsUsername: false,
  setUser: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }

    getMe()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem("token");
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAdmin: user?.role === "admin",
        needsUsername: !!user && !user.mc_username,
        setUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
