"""
Database initialization and base models for GiljoAI MCP
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Base class for all models
Base = declarative_base()

def get_database_url():
    """Get database URL from environment or use default SQLite"""
    db_type = os.getenv('DATABASE_TYPE', 'sqlite')

    if db_type == 'postgresql':
        host = os.getenv('PG_HOST', 'localhost')
        port = os.getenv('PG_PORT', '5432')
        database = os.getenv('PG_DATABASE', 'giljo_mcp')
        user = os.getenv('PG_USER', 'postgres')
        password = os.getenv('PG_PASSWORD', '')

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{user}@{host}:{port}/{database}"
    else:
        # SQLite
        db_path = os.getenv('DB_PATH', 'data/giljo_mcp.db')
        # Ensure the data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"

def init_database():
    """Initialize the database schema"""
    try:
        # Get database URL
        database_url = get_database_url()

        # Create engine
        if database_url.startswith('sqlite'):
            engine = create_engine(database_url, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(database_url)

        # Import all models to register them with Base
        try:
            from . import models  # This would import actual model definitions
        except ImportError:
            pass  # No models defined yet

        # Create all tables
        Base.metadata.create_all(bind=engine)

        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

def get_session():
    """Get a database session"""
    database_url = get_database_url()

    if database_url.startswith('sqlite'):
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(database_url)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

# Example model structure (to be expanded)
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Project(Base):
    """Project model for multi-tenant isolation"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    tenant_key = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)

class Agent(Base):
    """Agent model for orchestration"""
    __tablename__ = 'agents'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String(100), nullable=False)
    role = Column(String(100))
    status = Column(String(50), default='idle')
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", backref="agents")

class Message(Base):
    """Message model for inter-agent communication"""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    sender_id = Column(Integer, ForeignKey('agents.id'))
    receiver_id = Column(Integer, ForeignKey('agents.id'))
    content = Column(Text, nullable=False)
    message_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged = Column(Boolean, default=False)

    project = relationship("Project", backref="messages")
    sender = relationship("Agent", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("Agent", foreign_keys=[receiver_id], backref="received_messages")
