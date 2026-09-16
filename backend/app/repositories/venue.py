from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.venue import Venue
from app.schemas.venue import VenueCreate, VenueUpdate


def list_venues(db: Session) -> list[Venue]:
    return list(db.scalars(select(Venue).order_by(Venue.id)).all())


def get_venue(db: Session, venue_id: int) -> Venue | None:
    return db.get(Venue, venue_id)


def create_venue(db: Session, venue_data: VenueCreate) -> Venue:
    venue = Venue(**venue_data.model_dump())
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


def update_venue(db: Session, venue: Venue, venue_data: VenueUpdate) -> Venue:
    for field, value in venue_data.model_dump(exclude_unset=True).items():
        setattr(venue, field, value)

    db.commit()
    db.refresh(venue)
    return venue
