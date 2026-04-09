from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
from datetime import datetime
from core import ModManager, VoteManager, ServerManager, AuthManager
from models import User, Mod, ModVote, AuditLog, ModUpload, get_db, SessionLocal
from pydantic import BaseModel
import logging

# Initialize managers
mod_manager = ModManager()
vote_manager = VoteManager()
server_manager = ServerManager(
    server_path="/opt/minecraft/server",
    backup_path="/opt/minecraft/backups",
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

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class UserCreate(BaseModel):
    discord_id: str
    mc_username: Optional[str] = None
    role: str = "role1"

class ModCreate(BaseModel):
    name: str
    source_url: str
    curse_id: Optional[int] = None
    added_by: str
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None

class VoteCreate(BaseModel):
    mod_id: int
    vote_type: str  # add or remove
    initiated_by: str

class ModUploadCreate(BaseModel):
    filename: str
    file_hash: str
    uploaded_by: str

# Helper functions
def get_current_user(db: Session, token: str):
    try:
        payload = auth_manager.verify_access_token(token)
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.discord_id == user_id).first()
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_user_role(db: Session, user_id: str):
    user = db.query(User).filter(User.discord_id == user_id).first()
    return user.role if user else "role1"

# Routes
@app.get("/")
async def root():
    return {"message": "Mod Server Management API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/users/{discord_id}")
async def get_user(discord_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.discord_id == discord_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.discord_id == user.discord_id).first()
    if db_user:
        db_user.mc_username = user.mc_username
        db_user.role = user.role
        db.commit()
        db.refresh(db_user)
        return db_user
    
    db_user = User(
        discord_id=user.discord_id,
        mc_username=user.mc_username,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/users/{discord_id}")
async def update_user(discord_id: str, user_update: dict, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.discord_id == discord_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for key, value in user_update.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/mods")
async def list_mods(db: Session = Depends(get_db)):
    mods = db.query(Mod).all()
    return mods

@app.get("/mods/{mod_id}")
async def get_mod(mod_id: int, db: Session = Depends(get_db)):
    mod = db.query(Mod).filter(Mod.id == mod_id).first()
    if not mod:
        raise HTTPException(status_code=404, detail="Mod not found")
    return mod

@app.post("/mods")
async def create_mod(mod: ModCreate, db: Session = Depends(get_db)):
    db_mod = Mod(
        name=mod.name,
        source_url=mod.source_url,
        curse_id=mod.curse_id,
        added_by=mod.added_by,
        version=mod.version,
        description=mod.description,
        author=mod.author
    )
    db.add(db_mod)
    db.commit()
    db.refresh(db_mod)
    
    # Log audit
    audit = AuditLog(
        user_id=mod.added_by,
        action="Added mod",
        details=f"Added mod: {mod.name}",
        source="web"
    )
    db.add(audit)
    db.commit()
    
    return db_mod

@app.post("/mods/curseforge")
async def add_curseforge_mod(url: str, db: Session = Depends(get_db)):
    # Resolve CurseForge URL
    curse_mod = mod_manager.resolve_curseforge_url(url)
    if not curse_mod:
        raise HTTPException(status_code=400, detail="Invalid CurseForge URL")
    
    # Check if already exists
    existing_mod = db.query(Mod).filter(Mod.curse_id == curse_mod.id).first()
    if existing_mod:
        return existing_mod
    
    # Add new mod
    db_mod = Mod(
        name=curse_mod.name,
        source_url=url,
        curse_id=curse_mod.id,
        version=curse_mod.latest_file_name,
        added_by="system",
        status="active"
    )
    db.add(db_mod)
    db.commit()
    db.refresh(db_mod)
    
    return db_mod

@app.post("/mods/upload")
async def upload_mod(upload: ModUploadCreate, db: Session = Depends(get_db)):
    # Create upload record
    db_upload = ModUpload(
        filename=upload.filename,
        file_hash=upload.file_hash,
        uploaded_by=upload.uploaded_by,
        status="pending"
    )
    db.add(db_upload)
    db.commit()
    db.refresh(db_upload)
    
    return db_upload

@app.post("/votes")
async def create_vote(vote: VoteCreate, db: Session = Depends(get_db)):
    # Check if user has permission to vote
    user_role = get_user_role(db, vote.initiated_by)
    if user_role not in ["role1", "role2"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Create vote
    vote_obj = vote_manager.create_vote(
        mod_id=vote.mod_id,
        vote_type=vote.vote_type,
        initiated_by=vote.initiated_by
    )
    
    return vote_obj

@app.post("/votes/{vote_id}/vote")
async def vote(vote_id: int, vote: bool, db: Session = Depends(get_db)):
    # Check if user has permission to vote
    # This would typically check the user's role and permissions
    
    success = vote_manager.vote(vote_id, "user123", vote)  # Placeholder user ID
    
    if not success:
        raise HTTPException(status_code=400, detail="Vote not valid")
    
    return {"status": "success", "message": "Vote recorded"}

@app.post("/votes/{vote_id}/veto")
async def veto_vote(vote_id: int, db: Session = Depends(get_db)):
    # Check if user has permission to veto (Role 2)
    # This would check user's role
    
    success = vote_manager.veto(vote_id, "user123")  # Placeholder user ID
    
    if not success:
        raise HTTPException(status_code=400, detail="Veto not valid")
    
    return {"status": "success", "message": "Vote vetoed"}

@app.post("/server/update")
async def trigger_update(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Add to background task queue
    background_tasks.add_task(server_manager.run_update_loop)
    
    return {"status": "success", "message": "Update started"}

@app.post("/server/restart")
async def restart_server(db: Session = Depends(get_db)):
    success = server_manager.restart_server()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to restart server")
    
    # Log audit
    audit = AuditLog(
        user_id="system",
        action="Server restarted",
        details="Manual restart initiated",
        source="web"
    )
    db.add(audit)
    db.commit()
    
    return {"status": "success", "message": "Server restarting"}

@app.get("/audit")
async def get_audit_log(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()
    return logs

@app.get("/server/status")
async def get_server_status(db: Session = Depends(get_db)):
    # Simulate server status check
    return {
        "status": "online",
        "players_online": 12,
        "last_update": datetime.now().isoformat()
    }

@app.get("/server/backup")
async def create_backup(db: Session = Depends(get_db)):
    backup_file = server_manager.backup_world()
    
    if not backup_file:
        raise HTTPException(status_code=500, detail="Backup failed")
    
    return {"status": "success", "backup_file": backup_file}

@app.get("/server/history")
async def get_server_history(db: Session = Depends(get_db)):
    # Return server update history
    return {"history": []}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
