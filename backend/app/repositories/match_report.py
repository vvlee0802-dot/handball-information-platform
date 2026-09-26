from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match_report import (
    MatchReportImport,
    OfficialPlayerMatchStat,
    OfficialTeamMatchStat,
)
from app.models.player import Player


def get_report(db: Session, report_id: str) -> MatchReportImport | None:
    return db.get(MatchReportImport, report_id)


def find_report_by_checksum(
    db: Session, match_id: int, checksum_sha256: str
) -> MatchReportImport | None:
    return db.scalar(
        select(MatchReportImport).where(
            MatchReportImport.match_id == match_id,
            MatchReportImport.checksum_sha256 == checksum_sha256,
        )
    )


def latest_imported_report(db: Session, match_id: int) -> MatchReportImport | None:
    return db.scalar(
        select(MatchReportImport)
        .where(
            MatchReportImport.match_id == match_id,
            MatchReportImport.status == "imported",
        )
        .order_by(MatchReportImport.imported_at.desc(), MatchReportImport.created_at.desc())
        .limit(1)
    )


def list_player_stats(db: Session, report_id: str) -> list[OfficialPlayerMatchStat]:
    return list(
        db.scalars(
            select(OfficialPlayerMatchStat)
            .where(OfficialPlayerMatchStat.report_import_id == report_id)
            .order_by(OfficialPlayerMatchStat.team_id, OfficialPlayerMatchStat.number)
        ).all()
    )


def list_team_stats(db: Session, report_id: str) -> list[OfficialTeamMatchStat]:
    return list(
        db.scalars(
            select(OfficialTeamMatchStat)
            .where(OfficialTeamMatchStat.report_import_id == report_id)
            .order_by(OfficialTeamMatchStat.report_side)
        ).all()
    )


def find_player_by_team_and_number(db: Session, team_id: int, number: int) -> Player | None:
    return db.scalar(
        select(Player).where(Player.team_id == team_id, Player.number == number).limit(1)
    )


def find_or_create_report_player(
    db: Session,
    *,
    team_id: int,
    number: int,
    name: str,
) -> Player:
    player = find_player_by_team_and_number(db, team_id, number)
    if player is not None:
        player.name = name
        return player

    player = Player(
        name=name,
        number=number,
        position=None,
        team_id=team_id,
        birth_date=None,
        description="由官方赛后统计表导入，位置和出生日期待完善。",
    )
    db.add(player)
    db.flush()
    return player
