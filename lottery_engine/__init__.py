"""lottery_engine: A production-ready lottery draw library.

This package provides a clean, auditable, and deterministic lottery system
suitable for integration with web applications. It supports both seeded
(reproducible) and cryptographically secure (random) draws.

Example usage:
    >>> from lottery_engine import Entry, LotteryDraw
    >>> entries = [Entry(str(i)) for i in range(1, 96)]
    >>> draw = LotteryDraw(entries=entries, winners_to_pick=40, seed="my-seed")
    >>> draw.shuffle()
    >>> winner1 = draw.pick_next()
    >>> winner2 = draw.pick_next()
    >>> state = draw.state()
    >>> csv_export = draw.export_csv()
"""

from .core import LotteryDraw
from .models import Entry, Winner, DrawState, LotteryError

__version__ = "1.0.0"
__author__ = "lottery_engine"

# Public API exports
__all__ = [
    "LotteryDraw",
    "Entry", 
    "Winner",
    "DrawState",
    "LotteryError",
]