import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

/**
 * Handles the OAuth2 callback redirect from the backend.
 *
 * Flow:
 *   1. User clicks "Sign in with Discord" -> /api/auth/login
 *   2. Backend redirects to Discord -> Discord redirects to /api/auth/callback
 *   3. Backend exchanges code, creates JWT, redirects to /auth/callback?token=<jwt>
 *   4. This component stores the token and redirects to /
 */
export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    const err = searchParams.get("error");

    if (token) {
      localStorage.setItem("token", token);
      // Full reload so AuthContext picks up the new token
      window.location.href = "/";
    } else if (err) {
      setError(decodeURIComponent(err));
    } else {
      setError("No authentication token received");
    }
  }, [searchParams, navigate]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-space-dark">
        <div className="text-center">
          <p className="font-mono text-red-400">{error}</p>
          <a
            href="/"
            className="mt-4 inline-block font-mono text-sm text-gold underline"
          >
            Try again
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-space-dark">
      <div className="text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-gold border-t-transparent" />
        <p className="mt-4 font-mono text-sm text-white/40">Signing you in...</p>
      </div>
    </div>
  );
}
