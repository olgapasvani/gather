from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Event, EventStatus, EventView, User
from ..schemas import RecommendationResponse
from ..security import get_current_user
from ..services.recommendations import recommend

router = APIRouter(prefix="/api", tags=["recommendations"])


@router.post("/events/{event_id}/views", status_code=201)
def record_event_view(event_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = db.get(Event, event_id)
    if event is None or event.status != EventStatus.PUBLISHED:
        return {"recorded": False}
    db.add(EventView(event_id=event_id, user_id=user.id))
    db.commit()
    return {"recorded": True}


@router.get("/recommendations", response_model=list[RecommendationResponse])
def get_recommendations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return recommend(db, user.id)