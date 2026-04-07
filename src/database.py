"""
Database configuration and models for the activities management system.
Uses SQLite with SQLAlchemy ORM for persistent storage.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from pathlib import Path

# Database configuration
DATABASE_URL = "sqlite:///./mergington_activities.db"

# Create engine and session factory
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite specific
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Activity(Base):
    """Database model for extracurricular activities"""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    schedule = Column(String)
    max_participants = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityParticipant(Base):
    """Database model for activity participants (students)"""
    __tablename__ = "activity_participants"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, index=True)
    email = Column(String, index=True)
    signup_date = Column(DateTime, default=datetime.utcnow)


class Match(Base):
    """Database model for matches/competitions"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, index=True)
    activity_name = Column(String, index=True)
    match_date = Column(DateTime, index=True)
    location = Column(String)
    home_team = Column(String)
    away_team = Column(String)
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MatchResult(Base):
    """Database model for match results and scores"""
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, index=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    winner = Column(String, nullable=True)  # home, away, or tie
    recorded_by = Column(String)  # email of person recording result
    recorded_at = Column(DateTime, default=datetime.utcnow)


class Leaderboard(Base):
    """Database model for competition standings/leaderboard"""
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True, index=True)
    activity_name = Column(String, index=True)
    team_name = Column(String, index=True)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    points_for = Column(Integer, default=0)
    points_against = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize database and create tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency injection for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def populate_initial_data():
    """Populate database with initial activity data"""
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(Activity).first() is not None:
        db.close()
        return
    
    # Initial activities data
    initial_activities = [
        {
            "name": "Chess Club",
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        {
            "name": "Programming Class",
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        {
            "name": "Gym Class",
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
        {
            "name": "Soccer Team",
            "description": "Join the school soccer team and compete in matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 22,
            "participants": ["liam@mergington.edu", "noah@mergington.edu"]
        },
        {
            "name": "Basketball Team",
            "description": "Practice and play basketball with the school team",
            "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 15,
            "participants": ["ava@mergington.edu", "mia@mergington.edu"]
        },
        {
            "name": "Art Club",
            "description": "Explore your creativity through painting and drawing",
            "schedule": "Thursdays, 3:30 PM - 5:00 PM",
            "max_participants": 15,
            "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
        },
        {
            "name": "Drama Club",
            "description": "Act, direct, and produce plays and performances",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
            "max_participants": 20,
            "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
        },
        {
            "name": "Math Club",
            "description": "Solve challenging problems and participate in math competitions",
            "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
            "max_participants": 10,
            "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
        },
        {
            "name": "Debate Team",
            "description": "Develop public speaking and argumentation skills",
            "schedule": "Fridays, 4:00 PM - 5:30 PM",
            "max_participants": 12,
            "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
        }
    ]
    
    # Create activities and add participants
    try:
        for activity_data in initial_activities:
            activity = Activity(
                name=activity_data["name"],
                description=activity_data["description"],
                schedule=activity_data["schedule"],
                max_participants=activity_data["max_participants"]
            )
            db.add(activity)
            db.flush()
            
            # Add participants
            for email in activity_data["participants"]:
                participant = ActivityParticipant(
                    activity_id=activity.id,
                    email=email
                )
                db.add(participant)
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
