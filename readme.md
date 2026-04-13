<p align="center">
  <img src="https://img.shields.io/badge/MineShare-gold?style=for-the-badge&labelColor=010310&color=c09850" alt="MineShare" height="36"/>
</p>

<h1 align="center">
  <br/>
  MineShare
  <br/>
  <sub><sup>Collaborative Modded Minecraft Server Management</sup></sub>
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/Discord.py-5865F2?style=flat-square&logo=discord&logoColor=white" alt="Discord"/>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis"/>
</p>

<p align="center">
  A self-hosted platform that lets your friend group collaboratively manage a modded Minecraft server —<br/>
  add mods, vote on changes, track uptime, and download the modpack — all from a themed web app and Discord bot.
</p>

---

## What is MineShare?

Running a modded Minecraft server with friends shouldn't require one person to be the full-time sysadmin. MineShare gives everyone a say:

- **Want a new mod?** Paste a CurseForge link. MineShare validates it against your server's Minecraft version and NeoForge loader, then starts a vote.
- **Server updated a mod?** The changelog is pulled from CurseForge and posted to Discord automatically.
- **New player joining?** Give them the Discord role and they're whitelisted instantly. Send them the modpack download and they're ready to play.
- **Server crash at 3am?** Check the 30-day uptime bar from your phone to see exactly when it went down and came back.

Everything stays in sync — vote on Discord, see it update on the web app, and vice versa.

---

## Features

### Mod Management
- **CurseForge Integration** — Search, validate NeoForge + Minecraft version compatibility, auto-download, and auto-update mods
- **Version Validation** — Rejects mods that don't support your server's exact Minecraft version and mod loader
- **Upload Support** — Manually upload `.jar` files with virus scanning and admin approval
- **Mod Update Feed** — Changelogs pulled from CurseForge and posted to a `#mod-updates` Discord channel
- **Modpack Export** — One-click ZIP download containing every active mod JAR, ready to drop into a client instance

### Democratic Voting
- **Add & Remove Votes** — Members propose changes, everyone votes, quorum rules decide
- **Admin Powers** — Admins can veto, force-pass, or bypass voting entirely
- **Live Sync** — Vote from Discord buttons or the web app — tallies update everywhere in real time
- **Themed Embeds** — Every vote gets a generated banner image matching the web app's gold-on-space aesthetic

### Server Monitoring
- **30-Day Uptime History** — Statuspage.io-style uptime bar with 10-minute resolution
- **Player Count Graph** — 30-day area chart showing player activity over time
- **Daily Breakdown** — Color-coded daily uptime percentages at a glance
- **World Size Tracking** — See how big your world has grown
- **Live Status** — Current online/offline state and player list, updated every 30 seconds

### Role-Based Access
| Discord Role | App Role | Permissions |
|:--|:--|:--|
| Role 2 (OP) | **Admin** | Force add/remove, veto votes, approve uploads, server controls |
| Role 1 (Whitelist) | **Member** | Propose mods, vote, upload files, view everything |
| No role | **Guest** | View-only access, no whitelist |

Role changes in Discord sync instantly — add the role, they're whitelisted. Remove it, they're revoked.

### Automated Server Lifecycle
- **30-Minute Update Cycle** — Checks CurseForge for mod updates, stages changes, backs up the world, swaps mods, restarts gracefully
- **RCON Control** — In-game announcements, whitelist/OP management, player list, all via RCON
- **Backup System** — Automatic world backups before every update, with configurable retention
- **Health Checks** — Monitors server after restart, logs failures

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend    │────▶│  Minecraft   │
│  React/Vite  │ SSE │   FastAPI    │RCON │   Server     │
│  Tailwind    │◀────│  SQLAlchemy  │────▶│  NeoForge    │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  Discord Bot  │
                    │  discord.py   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Postgres │ │  Redis   │ │CurseForge│
        │   16     │ │  Pub/Sub │ │   API    │
        └──────────┘ └──────────┘ └──────────┘
```

| Service | Stack | Purpose |
|:--|:--|:--|
| **Backend** | FastAPI, SQLAlchemy, APScheduler | REST API, SSE events, scheduled update cycles |
| **Bot** | discord.py, persistent views | Discord integration, role sync, commands |
| **Frontend** | React 18, TypeScript, Tailwind, Framer Motion | Web dashboard with real-time updates |
| **Database** | PostgreSQL 16 | Mods, votes, uploads, heartbeats, audit logs |
| **Cache** | Redis 7 | Pub/sub event bus for cross-service sync |

### Event Flow

The system uses a **sync-from-DB** architecture — Discord channels are projections of database state, not append-only logs:

1. User action (web or Discord) → writes to DB → publishes Redis event
2. Bot receives event → queries DB for current state → upserts/deletes Discord messages
3. Periodic sync (every 2 minutes) acts as a safety net for missed events
4. On bot startup, a full sync rebuilds all channels from scratch

---

## Theme

MineShare uses a consistent **gold-on-space-dark** palette across every surface:

| Element | Color | Hex |
|:--|:--|:--|
| Background | Space Dark | `#010310` |
| Surface | Space Gray | `#0a0a1a` |
| Primary | Gold | `#c09850` |
| Primary Light | Gold Light | `#d4b06d` |
| Success | Emerald | `#10b981` |
| Danger | Red | `#ef4444` |
| Info | Blue | `#3b82f6` |
| Warning | Amber | `#f59e0b` |

Discord embeds use **Pillow-generated banner images** (1100px wide) that mirror the web app's aesthetic — starfield backgrounds, gold borders, corner ticks, and the same typography. This makes the Discord experience feel like a native extension of the web app rather than a generic bot.

---

## Pages

| Route | Page | Description |
|:--|:--|:--|
| `/` | **Dashboard** | Server status cards, active votes, pending uploads, recent activity |
| `/status` | **Server Status** | 30-day uptime bar, player count graph, daily breakdown, world size |
| `/mods` | **Mod Catalogue** | Browse/filter all mods, upload updates, vote to remove, export modpack |
| `/add-mod` | **Add Mod** | Paste a CurseForge URL (with compatibility preview) or upload a `.jar` |
| `/votes` | **Votes** | Active votes with inline voting, vote history |
| `/updates` | **Mod Updates** | Feed of all mod version changes with expandable changelogs |
| `/audit` | **Audit History** | Paginated log of every action across web, Discord, and system |
| `/admin` | **Admin Panel** | Server restart, backup, force update, pending upload review |

## Discord Channels

| Channel | Purpose |
|:--|:--|
| `#active-votes` | One message per pending vote — auto-created, auto-deleted on resolve |
| `#mod-uploads` | Pending upload approvals with Approve/Reject buttons |
| `#mod-proposals` | Live catalogue of all active mods with "Vote to Remove" buttons |
| `#server-status` | Single auto-updating message with uptime bar, player graph, stats |
| `#mod-updates` | Posted whenever a mod auto-updates — includes version diff and changelog |

### Bot Commands
| Command | Description |
|:--|:--|
| `!modlist` | Get a downloadable TXT + JSON of all active mods |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- A Discord Application with a Bot token
- A Minecraft server with RCON enabled
- *(Optional)* A CurseForge API key for mod integration

### 1. Clone

```bash
git clone https://github.com/your-org/project-mineshare.git
cd project-mineshare
```

### 2. Configure

Copy the example env and fill in your values:

```bash
cp backend/.env.example backend/.env
```

Key settings:

```env
# Discord
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_CLIENT_ID=your-client-id
DISCORD_CLIENT_SECRET=your-client-secret
DISCORD_GUILD_ID=your-guild-id
DISCORD_ROLE1_ID=whitelist-role-id
DISCORD_ROLE2_ID=admin-role-id

# Discord Channels
CHANNEL_ACTIVE_VOTES=channel-id
CHANNEL_MOD_PROPOSALS=channel-id
CHANNEL_MOD_UPLOADS=channel-id
CHANNEL_SERVER_STATUS=channel-id
CHANNEL_MOD_UPDATES=channel-id

# Minecraft
RCON_HOST=host.docker.internal
RCON_PORT=25575
RCON_PASSWORD=your-rcon-password

# CurseForge (optional — escape $ as $$)
CURSEFORGE_API_KEY=your-api-key
MINECRAFT_VERSION=1.21.5
```

### 3. Launch

```bash
docker compose up -d
```

This starts 5 services:
- **Backend API** on `http://localhost:8000`
- **Discord Bot** (connects automatically)
- **Frontend** on `http://localhost:3000`
- **PostgreSQL** on port `5432`
- **Redis** on port `6379`

### 4. Discord Setup

1. Invite the bot to your server with `applications.commands`, `bot` scopes and these permissions: Send Messages, Embed Links, Attach Files, Read Message History, Manage Messages
2. Create the five channels listed above and copy their IDs into `.env`
3. Make sure the bot can access all five channels

### 5. First Login

1. Visit `http://localhost:3000`
2. Click "Login with Discord"
3. Set your Minecraft username
4. You're in!

---

## Development

### Hot Reload

Both backend and frontend support hot reload via Docker volume mounts:

```yaml
# docker-compose.yml mounts ./backend:/app and ./frontend:/app
# Changes are picked up automatically — no rebuild needed
```

### Rebuilding

After changing dependencies (requirements.txt or package.json):

```bash
docker compose build --no-cache
docker compose up -d
```

### Database Migrations

MineShare uses auto-migration — tables are created by `Base.metadata.create_all` on startup, and new columns are added via idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements in the API lifespan handler.

---

## Project Structure

```
project-mineshare/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app factory + migrations
│   │   ├── deps.py              # Dependency injection
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── routes/
│   │       ├── auth.py          # Discord OAuth2 + JWT
│   │       ├── mods.py          # Mod CRUD + CurseForge
│   │       ├── votes.py         # Voting endpoints
│   │       ├── uploads.py       # File upload + approval
│   │       ├── server.py        # Status, uptime, modpack, updates
│   │       ├── users.py         # User profile
│   │       ├── audit.py         # Audit log
│   │       └── sse.py           # Server-Sent Events
│   ├── bot/
│   │   ├── bot.py               # Bot factory + persistent view registration
│   │   ├── theme.py             # Embed builders (gold/space palette)
│   │   ├── images.py            # Pillow banner generation
│   │   ├── views.py             # Persistent button views
│   │   └── cogs/
│   │       └── events_listener.py  # DB→Discord sync hub
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # SQLAlchemy engine
│   │   ├── events.py            # Redis pub/sub event bus
│   │   ├── mod_manager.py       # CurseForge API + version validation
│   │   ├── server_manager.py    # RCON, backups, mod swapping
│   │   ├── vote_manager.py      # Voting logic + quorum
│   │   ├── upload_manager.py    # File processing + scanning
│   │   ├── whitelist_manager.py # Role→whitelist/OP sync
│   │   └── scheduler.py         # 30-min update cycle
│   └── models/
│       └── __init__.py          # SQLAlchemy models
├── frontend/
│   └── src/
│       ├── App.tsx              # Router + auth gate
│       ├── components/          # All page components
│       ├── context/             # Auth context
│       ├── hooks/               # useSSE hook
│       └── lib/                 # API client, types, SSE
└── docker-compose.yml
```

---

## License

MIT License
