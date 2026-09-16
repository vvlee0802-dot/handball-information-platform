from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories import venue as venue_repository
from app.schemas.venue import VenueCreate, VenueRead, VenueUpdate


router = APIRouter(prefix="/api/venues", tags=["venues"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[VenueRead])
def list_venues(db: DatabaseSession) -> list[VenueRead]:
    return venue_repository.list_venues(db)


@router.post("", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
def create_venue(venue_data: VenueCreate, db: DatabaseSession) -> VenueRead:
    return venue_repository.create_venue(db, venue_data)


@router.get("/{venue_id}", response_model=VenueRead)
def get_venue(venue_id: int, db: DatabaseSession) -> VenueRead:
    venue = venue_repository.get_venue(db, venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


@router.patch("/{venue_id}", response_model=VenueRead)
def update_venue(
    venue_id: int,
    venue_data: VenueUpdate,
    db: DatabaseSession,
) -> VenueRead:
    venue = venue_repository.get_venue(db, venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue_repository.update_venue(db, venue, venue_data)
