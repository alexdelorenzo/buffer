from enum import Enum, auto
from abc import ABC


class Location(Enum):
    BeforeIndex = auto()
    Bisected = auto()
    AtIndex = auto()
    AfterIndex = auto()


class ChunkRead(ABC):
    def _chunk_before_index(self, offset: int, size: int) -> bytes:
        pass
    def _chunk_bisected_by_index(self, offset: int, size: int) -> bytes:
        pass
    def _chunk_at_index(self, size: int) -> bytes:
        pass
    def _chunk_after_index(self, offset: int, size: int) -> bytes:
        pass


class ChunkLocation(ABC):
    def _chunk_location(self, offset: int, size: int) -> Location:
        pass
