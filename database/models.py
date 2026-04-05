"""
Database Models - SQLAlchemy ORM models for Jarvis AI.
"""

import os
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class CommandLog(Base):
    __tablename__ = "command_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    command = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    response = Column(Text, default="")
    success = Column(Boolean, default=True)
    duration_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.now)


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    scheduled_time = Column(DateTime, nullable=False)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="pending")  # pending | completed | cancelled
    recurrence = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), default="")
    content = Column(Text, nullable=False)
    tags = Column(String(500), default="")
    category = Column(String(100), default="general")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    data_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.now)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), unique=True, nullable=False)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WikiArticle(Base):
    __tablename__ = "wiki_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(200), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text, default="")
    category = Column(String(100), default="General")
    tags = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
