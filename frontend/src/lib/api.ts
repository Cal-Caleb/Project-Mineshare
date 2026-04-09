import type {
  AuditEntry,
  CurseForgePreview,
  Mod,
  ServerEvent,
  ServerStatus,
  Upload,
  User,
  Vote,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "/api";

function getToken(): string | null {
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  opts: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(opts.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? res.statusText);
  }

  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────

export function getLoginUrl(): string {
  return `${BASE}/auth/login`;
}

export function getMe(): Promise<User> {
  return request<User>("/users/me");
}

export function setMinecraftUsername(mc_username: string): Promise<User> {
  return request<User>("/users/me/minecraft", {
    method: "PUT",
    body: JSON.stringify({ mc_username }),
  });
}

// ── Mods ─────────────────────────────────────────────────────────────

export function listMods(status?: string): Promise<Mod[]> {
  const q = status ? `?status=${status}` : "";
  return request<Mod[]>(`/mods${q}`);
}

export function getMod(id: number): Promise<Mod> {
  return request<Mod>(`/mods/${id}`);
}

export function previewCurseForge(url: string): Promise<CurseForgePreview> {
  return request<CurseForgePreview>("/mods/curseforge/preview", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function addCurseForgeMod(url: string, force = false): Promise<Mod> {
  return request<Mod>("/mods/curseforge", {
    method: "POST",
    body: JSON.stringify({ url, force }),
  });
}

export function removeMod(id: number, force = false): Promise<Mod> {
  return request<Mod>(`/mods/${id}?force=${force}`, { method: "DELETE" });
}

// ── Votes ────────────────────────────────────────────────────────────

export function listActiveVotes(): Promise<Vote[]> {
  return request<Vote[]>("/votes");
}

export function getVote(id: number): Promise<Vote> {
  return request<Vote>(`/votes/${id}`);
}

export function castBallot(voteId: number, in_favor: boolean): Promise<Vote> {
  return request<Vote>(`/votes/${voteId}/cast`, {
    method: "POST",
    body: JSON.stringify({ in_favor }),
  });
}

export function vetoVote(voteId: number): Promise<Vote> {
  return request<Vote>(`/votes/${voteId}/veto`, { method: "POST" });
}

export function forcePassVote(voteId: number): Promise<Vote> {
  return request<Vote>(`/votes/${voteId}/force-pass`, { method: "POST" });
}

export function getVoteHistory(limit = 20): Promise<Vote[]> {
  return request<Vote[]>(`/votes/history?limit=${limit}`);
}

// ── Uploads ──────────────────────────────────────────────────────────

export function uploadModJar(file: File): Promise<Upload> {
  const formData = new FormData();
  formData.append("file", file);
  return request<Upload>("/uploads", {
    method: "POST",
    body: formData,
  });
}

export function listPendingUploads(): Promise<Upload[]> {
  return request<Upload[]>("/uploads");
}

export function approveUpload(id: number, mod_name: string): Promise<Upload> {
  return request<Upload>(`/uploads/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ mod_name }),
  });
}

export function rejectUpload(id: number, reason = ""): Promise<Upload> {
  return request<Upload>(`/uploads/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

// ── Server ───────────────────────────────────────────────────────────

export function getServerStatus(): Promise<ServerStatus> {
  return request<ServerStatus>("/server/status");
}

export function triggerUpdate(): Promise<{ status: string; message: string }> {
  return request("/server/update", { method: "POST" });
}

export function restartServer(): Promise<{ status: string }> {
  return request("/server/restart", { method: "POST" });
}

export function createBackup(): Promise<{ status: string; backup_file: string }> {
  return request("/server/backup", { method: "POST" });
}

export function getServerEvents(limit = 20): Promise<ServerEvent[]> {
  return request<ServerEvent[]>(`/server/events?limit=${limit}`);
}

// ── Audit ────────────────────────────────────────────────────────────

export function getAuditLog(limit = 50, offset = 0): Promise<AuditEntry[]> {
  return request<AuditEntry[]>(`/audit?limit=${limit}&offset=${offset}`);
}
