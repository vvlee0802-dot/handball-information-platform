from datetime import date, time

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.competition import Competition
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.venue import Venue


def first_or_create(db, model, defaults: dict, **filters):
    instance = db.scalar(select(model).filter_by(**filters))
    if instance is not None:
        return instance, False
    instance = model(**filters, **defaults)
    db.add(instance)
    db.flush()
    return instance, True


def main() -> None:
    created: list[str] = []
    with SessionLocal() as db:
        competition, was_created = first_or_create(
            db,
            Competition,
            {"stage": "决赛阶段", "status": "completed"},
            name="示例手球锦标赛",
            season="2026",
        )
        if was_created:
            created.append("赛事")

        team_one, was_created = first_or_create(
            db,
            Team,
            {
                "short_name": "蓝队",
                "city": "上海",
                "country": "中国",
                "gender": "men",
                "description": "用于本地演示和验收的示例球队。",
            },
            name="示例蓝队",
        )
        if was_created:
            created.append("示例蓝队")

        team_two, was_created = first_or_create(
            db,
            Team,
            {
                "short_name": "橙队",
                "city": "北京",
                "country": "中国",
                "gender": "men",
                "description": "用于本地演示和验收的示例球队。",
            },
            name="示例橙队",
        )
        if was_created:
            created.append("示例橙队")

        venue, was_created = first_or_create(
            db,
            Venue,
            {
                "city": "上海",
                "address": "示例路 10 号",
                "capacity": 5000,
                "description": "用于本地演示和验收的示例场馆。",
            },
            name="示例手球馆",
        )
        if was_created:
            created.append("场馆")

        match, was_created = first_or_create(
            db,
            Match,
            {
                "venue_id": venue.id,
                "start_time": time(19, 30),
                "stage": "决赛",
                "status": "completed",
                "home_score": 32,
                "away_score": 29,
            },
            competition_id=competition.id,
            home_team_id=team_one.id,
            away_team_id=team_two.id,
            match_date=date(2026, 9, 28),
        )
        if was_created:
            created.append("比赛")

        for team, number, name, position in (
            (team_one, 7, "蓝队示例球员", "left_back"),
            (team_two, 10, "橙队示例球员", "centre_back"),
        ):
            _, was_created = first_or_create(
                db,
                Player,
                {
                    "name": name,
                    "position": position,
                    "description": "用于本地演示和验收的示例球员。",
                },
                team_id=team.id,
                number=number,
            )
            if was_created:
                created.append(name)

        db.commit()

    if created:
        print("Created demo records: " + ", ".join(created))
    else:
        print("Demo records already exist; no changes were required.")
    print(f"Demo match ID: {match.id}")


if __name__ == "__main__":
    main()
