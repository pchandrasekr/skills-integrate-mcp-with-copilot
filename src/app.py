"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.

Now uses SQLite database for persistent storage instead of in-memory data.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from .database import init_db, populate_initial_data, get_db, Activity, ActivityParticipant, Match, MatchResult, Leaderboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events (startup and shutdown)"""
    # Startup event
    init_db()
    populate_initial_data()
    yield
    # Shutdown event (cleanup if needed)


app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities",
              lifespan=lifespan)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


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


# ============ MATCH/COMPETITION TRACKING ENDPOINTS ============

@app.post("/matches/schedule")
def schedule_match(activity_name: str, match_date: str, location: str, 
                  home_team: str, away_team: str, db: Session = Depends(get_db)):
    """Schedule a new match for a competitive activity"""
    # Validate activity exists
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    try:
        from datetime import datetime
        match_datetime = datetime.fromisoformat(match_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    # Create match
    match = Match(
        activity_id=activity.id,
        activity_name=activity_name,
        match_date=match_datetime,
        location=location,
        home_team=home_team,
        away_team=away_team,
        status="scheduled"
    )
    db.add(match)
    db.commit()
    
    return {
        "match_id": match.id,
        "message": f"Match scheduled: {home_team} vs {away_team} on {match_date}",
        "status": "scheduled"
    }


@app.get("/matches/{activity_name}")
def get_matches_for_activity(activity_name: str, db: Session = Depends(get_db)):
    """Get all matches for a specific activity"""
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    matches = db.query(Match).filter(Match.activity_name == activity_name).all()
    
    matches_list = []
    for match in matches:
        result = db.query(MatchResult).filter(MatchResult.match_id == match.id).first()
        match_info = {
            "id": match.id,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "match_date": match.match_date.isoformat(),
            "location": match.location,
            "status": match.status,
            "result": None
        }
        if result:
            match_info["result"] = {
                "home_score": result.home_score,
                "away_score": result.away_score,
                "winner": result.winner
            }
        matches_list.append(match_info)
    
    return matches_list


@app.post("/matches/{match_id}/result")
def record_match_result(match_id: int, home_score: int, away_score: int, 
                       recorded_by: str, db: Session = Depends(get_db)):
    """Record the result and score of a completed match"""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Determine winner
    if home_score > away_score:
        winner = "home"
    elif away_score > home_score:
        winner = "away"
    else:
        winner = "tie"
    
    # Check if result already exists
    existing_result = db.query(MatchResult).filter(MatchResult.match_id == match_id).first()
    if existing_result:
        # Update existing result
        existing_result.home_score = home_score
        existing_result.away_score = away_score
        existing_result.winner = winner
        existing_result.recorded_by = recorded_by
        existing_result.recorded_at = datetime.utcnow()
    else:
        # Create new result
        result = MatchResult(
            match_id=match_id,
            home_score=home_score,
            away_score=away_score,
            winner=winner,
            recorded_by=recorded_by
        )
        db.add(result)
    
    # Update match status
    match.status = "completed"
    match.updated_at = datetime.utcnow()
    
    # Update leaderboard
    update_leaderboard(match, winner, home_score, away_score, db)
    
    db.commit()
    
    return {
        "match_id": match_id,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "home_score": home_score,
        "away_score": away_score,
        "winner": winner,
        "message": "Match result recorded"
    }


def update_leaderboard(match: Match, winner: str, home_score: int, away_score: int, db: Session):
    """Update leaderboard entries for teams after a match"""
    activity_name = match.activity_name
    
    # Get or create leaderboard entries for both teams
    home_lb = db.query(Leaderboard).filter(
        Leaderboard.activity_name == activity_name,
        Leaderboard.team_name == match.home_team
    ).first()
    if not home_lb:
        home_lb = Leaderboard(activity_name=activity_name, team_name=match.home_team)
        db.add(home_lb)
        db.flush()
    
    away_lb = db.query(Leaderboard).filter(
        Leaderboard.activity_name == activity_name,
        Leaderboard.team_name == match.away_team
    ).first()
    if not away_lb:
        away_lb = Leaderboard(activity_name=activity_name, team_name=match.away_team)
        db.add(away_lb)
        db.flush()
    
    # Update records
    if winner == "home":
        home_lb.wins += 1
        away_lb.losses += 1
    elif winner == "away":
        away_lb.wins += 1
        home_lb.losses += 1
    else:
        home_lb.ties += 1
        away_lb.ties += 1
    
    # Update points
    home_lb.points_for += home_score
    home_lb.points_against += away_score
    away_lb.points_for += away_score
    away_lb.points_against += home_score
    
    home_lb.updated_at = datetime.utcnow()
    away_lb.updated_at = datetime.utcnow()


@app.get("/leaderboard/{activity_name}")
def get_leaderboard(activity_name: str, db: Session = Depends(get_db)):
    """Get the leaderboard/standings for a competitive activity"""
    # Verify activity exists
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Get all leaderboard entries for this activity, sorted by wins/record
    standings = db.query(Leaderboard).filter(
        Leaderboard.activity_name == activity_name
    ).order_by(
        Leaderboard.wins.desc(),
        Leaderboard.ties.desc(),
        (Leaderboard.points_for - Leaderboard.points_against).desc()
    ).all()
    
    leaderboard = []
    for rank, entry in enumerate(standings, 1):
        leaderboard.append({
            "rank": rank,
            "team": entry.team_name,
            "wins": entry.wins,
            "losses": entry.losses,
            "ties": entry.ties,
            "points_for": entry.points_for,
            "points_against": entry.points_against,
            "point_differential": entry.points_for - entry.points_against
        })
    
    return leaderboard


@app.get("/matches/{match_id}")
def get_match_details(match_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific match"""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    result = db.query(MatchResult).filter(MatchResult.match_id == match_id).first()
    
    match_details = {
        "id": match.id,
        "activity": match.activity_name,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "match_date": match.match_date.isoformat(),
        "location": match.location,
        "status": match.status,
        "notes": match.notes,
        "result": None
    }
    
    if result:
        match_details["result"] = {
            "home_score": result.home_score,
            "away_score": result.away_score,
            "winner": result.winner,
            "recorded_by": result.recorded_by,
            "recorded_at": result.recorded_at.isoformat()
        }
    
    return match_details
