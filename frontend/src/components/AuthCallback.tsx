import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

/**
 * Handles the OAuth2 callback. The backend redirects here with
 * ?access_token=...&user=... after Discord auth.
 *
 * Actually, the backend /api/auth/callback returns JSON with the token.
 * So the flow is:
 *  1. Frontend opens /api/auth/login (redirects to Discord)
 *  2. Discord redirects back to /api/auth/callback
 *  3. Backend returns JSON { access_token, user }
 *
 * We need to handle this by having the frontend intercept the callback.
 * The simplest approach: backend redirects to frontend with token in hash.
 *
 * For now, the auth route returns JSON. The frontend opens the login URL
 * in the same window. We'll adjust the backend to redirect to frontend.
 */
export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      localStorage.setItem("token", token);
      navigate("/", { replace: true });
      window.location.reload();
    } else {
      // Try fetching from the API callback directly
      const code = searchParams.get("code");
      if (code) {
        const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
        fetch(`${apiUrl}/auth/callback?code=${code}`)
          .then((r) => r.json())
          .then((data) => {
            if (data.access_token) {
              localStorage.setItem("token", data.access_token);
              navigate("/", { replace: true });
              window.location.reload();
            } else {
              setError("Authentication failed");
            }
          })
          .catch(() => setError("Authentication failed"));
      } else {
        setError("No auth code received");
      }
    }
  }, [searchParams, navigate]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-space-dark">
        <div className="text-center">
          <p className="font-mono text-red-400">{error}</p>
          <a href="/" className="mt-4 inline-block font-mono text-sm text-gold underline">
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
