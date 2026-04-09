from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String, unique=True, index=True)
    mc_username = Column(String, nullable=True)
    role = Column(String, default="role1")  # role1, role2, role3
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_whitelisted = Column(Boolean, default=False)
    is_op = Column(Boolean, default=False)

class Mod(Base):
    __tablename__ = "mods"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    source_url = Column(String)
    curse_id = Column(Integer, nullable=True)
    file_hash = Column(String)
    added_by = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")  # active, inactive, pending, removed
    version = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=True)
    download_count = Column(Integer, default=0)

class ModVote(Base):
    __tablename__ = "mod_votes"
    
    id = Column(Integer, primary_key=True, index=True)
    mod_id = Column(Integer, index=True)
    voter_id = Column(String)
    vote_type = Column(String)  # add, remove
    vote = Column(Boolean)  # True for yes, False for no
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_veto = Column(Boolean, default=False)
    is_force_approved = Column(Boolean, default=False)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String)
    action = Column(String)
    details = Column(Text)
    source = Column(String)  # web, discord, bot, system

class ModUpload(Base):
    __tablename__ = "mod_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    file_hash = Column(String)
    status = Column(String, default="pending")  # pending, approved, rejected, quarantined
    uploaded_by = Column(String)
    approved_by = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    quarantine_path = Column(String, nullable=True)
    scan_result = Column(String, nullable=True)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./modserver.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
