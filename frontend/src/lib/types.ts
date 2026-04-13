// ── Users ────────────────────────────────────────────────────────────

export interface User {
  id: number;
  discord_id: string;
  discord_username: string;
  discord_avatar: string | null;
  mc_username: string | null;
  role: "guest" | "member" | "admin";
  is_whitelisted: boolean;
  is_op: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ── Mods ─────────────────────────────────────────────────────────────

export interface Mod {
  id: number;
  name: string;
  slug: string | null;
  description: string | null;
  author: string | null;
  source: "curseforge" | "upload";
  source_url: string | null;
  curse_project_id: number | null;
  current_version: string | null;
  file_name: string | null;
  status: "active" | "pending_vote" | "pending_approval" | "removed";
  download_count: number;
  added_by?: User;
  created_at: string;
  updated_at: string;
}

export interface CurseForgePreview {
  project_id: number;
  name: string;
  slug: string;
  summary: string;
  author: string;
  logo_url: string | null;
  latest_file_name: string | null;
  download_count: number;
  supports_neoforge: boolean;
  game_versions: string[];
}

// ── Votes ────────────────────────────────────────────────────────────

export interface VoteTally {
  yes: number;
  no: number;
  total: number;
}

export interface Ballot {
  id: number;
  user: User;
  in_favor: boolean;
  cast_at: string;
}

export interface Vote {
  id: number;
  mod: Mod;
  vote_type: "add" | "remove";
  initiated_by: User | null;
  status: "pending" | "approved" | "rejected" | "vetoed" | "force_approved" | "expired";
  created_at: string;
  expires_at: string;
  resolved_at: string | null;
  tally: VoteTally | null;
  ballots: Ballot[];
}

// ── Uploads ──────────────────────────────────────────────────────────

export interface Upload {
  id: number;
  original_filename: string;
  file_hash: string;
  file_size: number;
  status: string;
  scan_result: string | null;
  mod_id: number | null;
  uploaded_by?: User;
  approved_by?: User;
  created_at: string;
  resolved_at: string | null;
}

// ── Audit ────────────────────────────────────────────────────────────

export interface AuditEntry {
  id: number;
  user: User | null;
  action: string;
  details: string | null;
  source: "web" | "discord" | "system";
  created_at: string;
}

// ── Server ───────────────────────────────────────────────────────────

export interface ServerStatus {
  online: boolean;
  players: string[];
  player_count: number;
}

export interface ServerEvent {
  id: number;
  event_type: string;
  status: string;
  details: string | null;
  backup_path: string | null;
  created_at: string;
  completed_at: string | null;
}

// ── Uptime ──────────────────────────────────────────────────────────

export interface UptimeBucket {
  bucket: string;
  online: boolean | null;
  player_count: number;
}

export interface UptimeStats {
  uptime_pct: number;
  buckets: UptimeBucket[];
  peak_players: number;
  avg_players: number;
  world_size_mb: number | null;
}

// ── Mod Updates ─────────────────────────────────────────────────────

export interface ModUpdate {
  id: number;
  mod_id: number;
  mod_name: string;
  mod_slug: string | null;
  old_version: string | null;
  new_version: string | null;
  changelog: string | null;
  source_url: string | null;
  created_at: string;
}

// ── Mod Export ───────────────────────────────────────────────────────

export interface ModExportEntry {
  name: string;
  author: string | null;
  source: string;
  curse_project_id: number | null;
  file_name: string | null;
  source_url: string | null;
  current_version: string | null;
}

export interface ModExport {
  name: string;
  mod_count: number;
  mods: ModExportEntry[];
}
