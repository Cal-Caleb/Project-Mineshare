# Mod Server Management System

A fully automated modded Minecraft server management system with web UI and Discord bot integration.

## Features

- **Self-Updating Server**: Automatically checks for CurseForge mod updates every 30 minutes
- **Collaborative Mod Management**: Friends can add/remove mods without technical knowledge
- **Role-Based Permissions**: 
  - Role 1: Regular users (can propose, vote)
  - Role 2: Admins (can force add/remove, veto)
- **Web UI & Discord Bot**: 100% interoperable with shared backend logic
- **Security**: Virus scanning, quarantine, audit logging
- **Automated Server Management**: Backup, restart, health checks

## Architecture

### Backend
- FastAPI (Python) with PostgreSQL
- Discord bot using discord.py
- Redis for real-time communication
- RCON for Minecraft server control
- ClamAV for virus scanning

### Frontend
- React + TypeScript + Tailwind CSS
- Space-themed UI with starfield background
- Responsive design with Framer Motion animations

### Components
1. **Mod Management**: CurseForge resolution, custom uploads
2. **Voting System**: Democratic voting with quorum and majority rules
3. **Server Control**: Automated updates, backups, restarts
4. **Authentication**: Discord OAuth2 + JWT tokens
5. **Audit Logging**: Complete history of all actions

## Installation

1. Clone the repository
2. Set up environment variables in `.env`
3. Run `docker-compose up` to start all services
4. Access the web UI at `http://localhost:3000`
5. Invite the Discord bot to your server

## Usage

### Web UI
- Dashboard: Server status and recent activity
- Mod Catalogue: Browse all installed mods
- Add Mod: Add from CurseForge or upload .jar
- Active Votes: View and vote on pending proposals
- Audit History: Complete log of all actions
- Admin Panel: Force actions and server management

### Discord Bot
- `/addmod [url]`: Add mod from CurseForge
- `/uploadmod`: Upload custom .jar file
- `/removemod [name]`: Remove a mod
- `/vote [mod_name] [yes/no]`: Vote on a mod
- `/forceadd [url]`: Force add a mod (Role 2)
- `/veto [mod_name]`: Veto a vote (Role 2)
- `/forceupdate`: Force server update (Role 2)

## Security

- Discord OAuth2 authentication
- Role-based access control
- File virus scanning with ClamAV
- Quarantine for custom uploads
- Audit logging for all actions
- Rate limiting and CSRF protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License
