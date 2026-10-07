from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.event_player_assignment_audit import EventPlayerAssignmentAudit
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.repositories import match_report as match_reports
from app.schemas.player_stats import MatchPlayerStatsRead, PlayerMatchStatsRead, PlayerStatsMetric

METRIC_EVENT_TYPES: dict[PlayerStatsMetric, tuple[str, ...]] = {
    "goals": ("goal",),
    "shots": ("goal", "shot"),
    "saves": ("save",),
    "turnovers": ("turnover",),
    "fast_breaks": ("fast_break",),
}


def get_match_player_stats(
    db: Session,
    match: Match,
) -> MatchPlayerStatsRead:
    teams = {
        team.id: team
        for team in db.scalars(
            select(Team).where(Team.id.in_((match.home_team_id, match.away_team_id)))
        )
    }
    players = list(
        db.scalars(
            select(Player)
            .where(Player.team_id.in_((match.home_team_id, match.away_team_id)))
            .order_by(Player.team_id, Player.number, Player.id)
        )
    )
    report = match_reports.latest_imported_report(db, match.id)
    official_goals: dict[int, int] = {}
    if report is not None:
        for stat in match_reports.list_player_stats(db, report.id):
            if stat.player_id is not None:
                official_goals[stat.player_id] = stat.goals

    rows: list[PlayerMatchStatsRead] = []
    for player in players:
        rows.append(
            PlayerMatchStatsRead(
                player_id=player.id,
                player_name=player.name,
                player_number=player.number,
                position=player.position,
                team_id=player.team_id,
                team_name=teams[player.team_id].name,
                goals=official_goals.get(player.id, 0),
                shots=0,
                saves=0,
                turnovers=0,
                fast_breaks=0,
                shooting_percentage=None,
            )
        )

    return MatchPlayerStatsRead(
        match_id=match.id,
        home_team_id=match.home_team_id,
        home_team_name=teams[match.home_team_id].name,
        away_team_id=match.away_team_id,
        away_team_name=teams[match.away_team_id].name,
        home_score=match.home_score,
        away_score=match.away_score,
        goal_source="official_report" if report is not None else "unavailable",
        official_report_id=report.id if report is not None else None,
        players=rows,
    )


def list_player_metric_events(
    db: Session,
    *,
    match_id: int,
    player_id: int,
    metric: PlayerStatsMetric,
) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(
                Event.match_id == match_id,
                Event.player_id == player_id,
                Event.event_type.in_(METRIC_EVENT_TYPES[metric]),
                Event.status == "verified",
                Event.deleted_at.is_(None),
            )
            .order_by(Event.timestamp_seconds, Event.id)
        )
    )


def reassign_events_to_player(
    db: Session,
    *,
    events: list[Event],
    new_player: Player,
    changed_by_user_id: int,
    changed_by_user_name: str,
) -> tuple[int, list[Event]]:
    old_player_ids = {event.player_id for event in events if event.player_id is not None}
    old_players = {
        player.id: player
        for player in db.scalars(select(Player).where(Player.id.in_(old_player_ids)))
    }
    affected_count = 0
    for event in events:
        if event.player_id == new_player.id:
            continue
        old_player = old_players.get(event.player_id)
        db.add(
            EventPlayerAssignmentAudit(
                match_id=event.match_id,
                event_id=event.id,
                old_player_id=event.player_id,
                old_player_name=old_player.name if old_player else None,
                new_player_id=new_player.id,
                new_player_name=new_player.name,
                changed_by_user_id=changed_by_user_id,
                changed_by_user_name=changed_by_user_name,
            )
        )
        event.player_id = new_player.id
        event.team_id = new_player.team_id
        event.updated_by_user_id = changed_by_user_id
        affected_count += 1
    db.commit()
    for event in events:
        db.refresh(event)
    return affected_count, events


def list_player_assignment_audits(
    db: Session,
    *,
    match_id: int,
) -> list[EventPlayerAssignmentAudit]:
    return list(
        db.scalars(
            select(EventPlayerAssignmentAudit)
            .where(EventPlayerAssignmentAudit.match_id == match_id)
            .order_by(
                EventPlayerAssignmentAudit.changed_at.desc(),
                EventPlayerAssignmentAudit.id.desc(),
            )
        )
    )
