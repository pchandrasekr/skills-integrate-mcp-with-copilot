"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.

Now uses SQLite database for persistent storage instead of in-memory data.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from sqlalchemy.orm import Session

from database import init_db, populate_initial_data, get_db, Activity, ActivityParticipant

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database and populate with initial data"""
    init_db()
    populate_initial_data()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(db: Session = Depends(get_db)):
    """Get all activities with their participant counts"""
    activities_list = []
    
    for activity in db.query(Activity).all():
        participant_count = db.query(ActivityParticipant).filter(
            ActivityParticipant.activity_id == activity.id
        ).count()
        
        participants = db.query(ActivityParticipant.email).filter(
            ActivityParticipant.activity_id == activity.id
        ).all()
        
        activities_list.append({
            "name": activity.name,
            "description": activity.description,
            "schedule": activity.schedule,
            "max_participants": activity.max_participants,
            "participants": [p[0] for p in participants]
        })
    
    return {activity["name"]: activity for activity in activities_list}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    """Sign up a student for an activity"""
    # Validate activity exists
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is not already signed up
    existing_signup = db.query(ActivityParticipant).filter(
        ActivityParticipant.activity_id == activity.id,
        ActivityParticipant.email == email
    ).first()
    
    if existing_signup:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    participant = ActivityParticipant(activity_id=activity.id, email=email)
    db.add(participant)
    db.commit()
    
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    """Unregister a student from an activity"""
    # Validate activity exists
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is signed up
    participant = db.query(ActivityParticipant).filter(
        ActivityParticipant.activity_id == activity.id,
        ActivityParticipant.email == email
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    db.delete(participant)
    db.commit()
    
    return {"message": f"Unregistered {email} from {activity_name}"}
