import asyncio
import datetime
from typing import Any, TypedDict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import sessionmanager
from core.enums import EventStatus, EventType, UserRole
from core.security import hash_password
from models.event import Event
from models.room import Room
from models.user import User


class RoomSeedPayload(TypedDict):
    name: str
    capacity: int
    location: str
    equipment: dict[str, Any]
    is_available: bool


class RoomSeedResult(TypedDict):
    id: UUID
    name: str


class CuratorSeedPayload(TypedDict):
    login: str
    raw_password: str
    telegram_username: str | None


class CuratorSeedResult(TypedDict):
    id: UUID
    login: str


class EventSeedPayload(TypedDict):
    title: str
    description: str
    event_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    max_participants: int | None
    creator_login: str
    curator_login: str
    room_name: str


async def seed_rooms(*, session: AsyncSession, payloads: list[RoomSeedPayload]) -> dict[str, RoomSeedResult]:
    result: dict[str, RoomSeedResult] = {}
    for payload in payloads:
        existing = await session.scalar(select(Room).where(Room.name == payload["name"]))
        if existing is not None:
            result[payload["name"]] = {"id": existing.id, "name": existing.name}
            continue
        room = Room(
            name=payload["name"],
            capacity=payload["capacity"],
            location=payload["location"],
            equipment=payload["equipment"],
            is_available=payload["is_available"],
        )
        session.add(room)
        await session.flush()
        result[payload["name"]] = {"id": room.id, "name": room.name}
    await session.commit()
    return result


async def seed_curators(
    *,
    session: AsyncSession,
    payloads: list[CuratorSeedPayload],
) -> dict[str, CuratorSeedResult]:
    result: dict[str, CuratorSeedResult] = {}
    for payload in payloads:
        existing = await session.scalar(select(User).where(User.login == payload["login"]))
        if existing is not None:
            result[payload["login"]] = {"id": existing.id, "login": existing.login}
            continue
        user = User(
            login=payload["login"],
            password_hash=hash_password(payload["raw_password"]),
            role=UserRole.CURATOR,
            telegram_username=payload["telegram_username"],
        )
        session.add(user)
        await session.flush()
        result[payload["login"]] = {"id": user.id, "login": user.login}
    await session.commit()
    return result


async def seed_events(
    *,
    session: AsyncSession,
    payloads: list[EventSeedPayload],
    curators: dict[str, CuratorSeedResult],
    rooms: dict[str, RoomSeedResult],
) -> None:
    for payload in payloads:
        existing = await session.scalar(select(Event).where(Event.title == payload["title"]))
        if existing is not None:
            continue
        if payload["creator_login"] not in curators:
            raise ValueError(f"Creator {payload['creator_login']} missing for event {payload['title']}")
        if payload["curator_login"] not in curators:
            raise ValueError(f"Curator {payload['curator_login']} missing for event {payload['title']}")
        if payload["room_name"] not in rooms:
            raise ValueError(f"Room {payload['room_name']} missing for event {payload['title']}")
        event = Event(
            title=payload["title"],
            description=payload["description"],
            event_date=payload["event_date"],
            start_time=payload["start_time"],
            end_time=payload["end_time"],
            registered_count=0,
            max_participants=payload["max_participants"],
            status=EventStatus.APPROVED,
            event_type=EventType.OFFICIAL,
            creator_id=curators[payload["creator_login"]]["id"],
            curator_id=curators[payload["curator_login"]]["id"],
            is_external_venue=False,
            room_id=rooms[payload["room_name"]]["id"],
            external_location=None,
            need_approve_candidates=False,
        )
        session.add(event)
    await session.commit()


async def run_seed() -> None:
    if sessionmanager.session_maker is None:
        raise RuntimeError("Database sessionmaker is not initialized")
    async with sessionmanager.session_maker() as session:
        rooms = await seed_rooms(
            session=session,
            payloads=[
                {
                    "name": "B504",
                    "capacity": 120,
                    "location": "Корпус B, 5 этаж",
                    "equipment": {"projector": True, "sound_system": True},
                    "is_available": True,
                },
                {
                    "name": "B502",
                    "capacity": 90,
                    "location": "Корпус B, 5 этаж",
                    "equipment": {"projector": True, "board": True},
                    "is_available": True,
                },
                {
                    "name": "B506",
                    "capacity": 70,
                    "location": "Корпус B, 5 этаж",
                    "equipment": {"projector": True},
                    "is_available": True,
                },
            ],
        )
        curators = await seed_curators(
            session=session,
            payloads=[
                {
                    "login": "curator_alex",
                    "raw_password": "curator_alex_password",
                    "telegram_username": "alex_curator",
                },
                {
                    "login": "curator_maria",
                    "raw_password": "curator_maria_password",
                    "telegram_username": "maria_curator",
                },
            ],
        )
        today = datetime.date.today()
        await seed_events(
            session=session,
            curators=curators,
            rooms=rooms,
            payloads=[
                {
                    "title": "Официальная презентация стартапов",
                    "description": "Презентация проектов с участием студентов и кураторов.",
                    "event_date": today + datetime.timedelta(days=7),
                    "start_time": datetime.time(hour=10, minute=0),
                    "end_time": datetime.time(hour=12, minute=0),
                    "max_participants": 120,
                    "creator_login": "curator_alex",
                    "curator_login": "curator_alex",
                    "room_name": "B504",
                },
                {
                    "title": "Официальная стратегическая сессия",
                    "description": "Сессия по планированию мероприятий на семестр.",
                    "event_date": today + datetime.timedelta(days=14),
                    "start_time": datetime.time(hour=14, minute=0),
                    "end_time": datetime.time(hour=16, minute=0),
                    "max_participants": 90,
                    "creator_login": "curator_maria",
                    "curator_login": "curator_alex",
                    "room_name": "B502",
                },
            ],
        )
async def main_async() -> None:
    await run_seed()
    await sessionmanager.close()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

