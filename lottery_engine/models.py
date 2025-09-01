"""Data models and exceptions for the lottery_engine library.

This module contains all dataclasses and custom exceptions used throughout
the lottery system. All models are designed to be immutable and type-safe.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


class LotteryError(Exception):
    """Base exception class for all lottery-related errors.
    
    This exception is raised when invalid operations are attempted,
    such as picking winners before shuffling or exceeding the maximum
    number of winners.
    """
    pass


@dataclass(frozen=True)
class Entry:
    """Represents a single lottery entry.
    
    An entry consists of a registration number (required) and an optional
    human-readable label. The registration number serves as the unique
    identifier for the entry.
    
    Args:
        registration_no: Unique identifier for the entry.
        label: Optional human-readable description of the entry.
    """
    registration_no: str
    label: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate the entry after initialization."""
        if not self.registration_no:
            raise LotteryError("Registration number cannot be empty")


@dataclass(frozen=True)
class Winner:
    """Represents a lottery winner with their draw information.
    
    Contains the winner's registration number, their rank in the draw
    (1-based ordering), and the timestamp when they were selected.
    
    Args:
        registration_no: The registration number of the winning entry.
        rank: The position in which this winner was drawn (1-based).
        picked_at: The datetime when this winner was selected.
    """
    registration_no: str
    rank: int
    picked_at: datetime
    
    def __post_init__(self) -> None:
        """Validate the winner after initialization."""
        if not self.registration_no:
            raise LotteryError("Registration number cannot be empty")
        if self.rank <= 0:
            raise LotteryError("Rank must be positive")


@dataclass(frozen=True)
class DrawState:
    """Represents the complete state of a lottery draw.
    
    This immutable snapshot contains all information about the current
    state of a lottery draw, including winners, remaining entries,
    counts, status, and audit information.
    
    Args:
        winners: List of winners drawn so far, in order of selection.
        remaining: List of registration numbers still in the draw.
        picked_count: Number of winners selected so far.
        total: Total number of entries in the original draw.
        winners_to_pick: Total number of winners to be selected.
        status: Current status of the draw (Draft/Shuffled/Completed).
        input_hash: SHA256 hash of the original input for audit purposes.
    """
    winners: List[Winner]
    remaining: List[str]
    picked_count: int
    total: int
    winners_to_pick: int
    status: str
    input_hash: str
    
    def __post_init__(self) -> None:
        """Validate the draw state after initialization."""
        if self.picked_count < 0:
            raise LotteryError("Picked count cannot be negative")
        if self.total < 0:
            raise LotteryError("Total entries cannot be negative")
        if self.winners_to_pick <= 0:
            raise LotteryError("Winners to pick must be positive")
        if self.winners_to_pick > self.total:
            raise LotteryError("Cannot pick more winners than total entries")
        if len(self.winners) != self.picked_count:
            raise LotteryError("Winners list length must match picked count")
        if self.status not in ("Draft", "Shuffled", "Completed"):
            raise LotteryError(f"Invalid status: {self.status}")
        if not self.input_hash:
            raise LotteryError("Input hash cannot be empty")