from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from typing import Optional
import uvicorn
from core import ModManager, VoteManager, ServerManager, AuthManager

# Initialize managers
mod_manager = ModManager()
vote_manager = VoteManager()
server_manager = ServerManager(
    server_path="/path/to/minecraft/server",
    backup_path="/path/to/backups",
    rcon_host="localhost",
    rcon_port=25575,
    rcon_password="rconpassword"
)
auth_manager = AuthManager(
    discord_client_id="your_discord_client_id",
    discord_client_secret="your_discord_client_secret",
    jwt_secret="your_jwt_secret"
)

app = FastAPI(title="Mod Server Management API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Sample routes
@app.get("/")
async def root():
    return {"message": "Mod Server Management API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/mods")
async def list_mods():
    # This would be implemented with database access
    return {"mods": []}

@app.post("/mods/add")
async def add_mod(mod_data: dict):
    # Add logic to handle mod addition
    return {"status": "success", "message": "Mod added successfully"}

@app.post("/mods/remove")
async def remove_mod(mod_id: int):
    # Add logic to handle mod removal
    return {"status": "success", "message": "Mod removed successfully"}

@app.get("/votes")
async def list_votes():
    # This would be implemented with database access
    return {"votes": []}

@app.post("/votes/{vote_id}/vote")
async def vote(vote_id: int, vote: bool):
    # Add logic to handle voting
    return {"status": "success", "message": "Vote recorded"}

@app.post("/server/update")
async def trigger_update():
    # Trigger manual update
    success = server_manager.run_update_loop()
    if success:
        return {"status": "success", "message": "Update completed"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Update failed"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
