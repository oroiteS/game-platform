from __future__ import annotations

from typing import Protocol

from app.platform.models import Room


class RoomStorageError(RuntimeError):
    pass


class RoomStorage(Protocol):
    def list_room_codes(self) -> set[str]:
        ...

    def get_room(self, room_code: str) -> Room | None:
        ...

    def save_room(self, room: Room) -> None:
        ...

    def delete_room(self, room_code: str) -> None:
        ...


class InMemoryRoomStorage:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def list_room_codes(self) -> set[str]:
        return set(self._rooms)

    def get_room(self, room_code: str) -> Room | None:
        return self._rooms.get(room_code)

    def save_room(self, room: Room) -> None:
        self._rooms[room.room_code] = room

    def delete_room(self, room_code: str) -> None:
        self._rooms.pop(room_code, None)
