from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MatchReportImport(Base):
    __tablename__ = "match_report_imports"
    __table_args__ = (
        UniqueConstraint("match_id", "checksum_sha256", name="uq_match_report_match_checksum"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )
    parsed_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    conflicts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    team_a_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True
    )
    team_b_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=True
    )
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OfficialPlayerMatchStat(Base):
    __tablename__ = "official_player_match_stats"
    __table_args__ = (
        UniqueConstraint(
            "report_import_id",
            "team_id",
            "number",
            name="uq_official_player_stat_report_team_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    report_import_id: Mapped[str] = mapped_column(
        ForeignKey("match_report_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True
    )
    player_name: Mapped[str] = mapped_column(String(120), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    goals: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    suspensions_2min: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    red_cards: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    blue_cards: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


class OfficialTeamMatchStat(Base):
    __tablename__ = "official_team_match_stats"
    __table_args__ = (
        UniqueConstraint("report_import_id", "team_id", name="uq_official_team_stat_report_team"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    report_import_id: Mapped[str] = mapped_column(
        ForeignKey("match_report_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    report_side: Mapped[str] = mapped_column(String(1), nullable=False)
    half_time_score: Mapped[int] = mapped_column(Integer, nullable=False)
    final_score: Mapped[int] = mapped_column(Integer, nullable=False)
    seven_meter_goals: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    seven_meter_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    timeouts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

