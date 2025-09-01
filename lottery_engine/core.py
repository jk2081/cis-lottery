"""Core lottery draw implementation.

This module contains the main LotteryDraw class that handles all lottery
logic including initialization, shuffling, winner selection, and state management.
"""

import csv
import hashlib
import io
import json
import random
import secrets
from datetime import datetime
from typing import List, Optional

from .models import Entry, Winner, DrawState, LotteryError


class LotteryDraw:
    """Main lottery draw engine with deterministic and cryptographic modes.
    
    This class manages the complete lifecycle of a lottery draw, from
    initialization through winner selection. It supports both deterministic
    draws (with seed) for audit reproducibility and cryptographically
    secure draws (without seed) for maximum fairness.
    
    The draw follows a strict state machine:
    Draft → Shuffled → Completed
    
    Args:
        entries: List of Entry objects to include in the draw.
        winners_to_pick: Number of winners to select from the entries.
        seed: Optional seed for deterministic shuffling. If None, uses
              cryptographically secure randomization.
    
    Raises:
        LotteryError: If invalid parameters are provided.
    """
    
    def __init__(self, entries: List[Entry], winners_to_pick: int, seed: Optional[str] = None):
        """Initialize a new lottery draw."""
        if not entries:
            raise LotteryError("Entries list cannot be empty")
        if winners_to_pick <= 0:
            raise LotteryError("Winners to pick must be positive")
        if winners_to_pick > len(entries):
            raise LotteryError("Cannot pick more winners than available entries")
        
        # Validate all entries have unique registration numbers
        reg_nos = [entry.registration_no for entry in entries]
        if len(reg_nos) != len(set(reg_nos)):
            raise LotteryError("All entries must have unique registration numbers")
        
        self._original_entries = list(entries)  # Immutable copy
        self._winners_to_pick = winners_to_pick
        self._seed = seed
        self._status = "Draft"
        self._winners: List[Winner] = []
        self._shuffled_sequence: List[str] = []
        self._current_position = 0
        
        # Compute input hash for audit integrity
        self._input_hash = self._compute_input_hash(entries, winners_to_pick, seed)
    
    def _compute_input_hash(self, entries: List[Entry], winners_to_pick: int, seed: Optional[str]) -> str:
        """Compute SHA256 hash of normalized input for audit purposes.
        
        Creates a deterministic hash based on the entries (sorted by registration_no),
        winners_to_pick, and seed. This enables audit verification.
        
        Args:
            entries: List of entries to hash.
            winners_to_pick: Number of winners to pick.
            seed: Optional seed value.
        
        Returns:
            Hexadecimal SHA256 hash string.
        """
        # Sort entries by registration_no for consistent hashing
        sorted_entries = sorted(entries, key=lambda e: e.registration_no)
        
        # Create normalized representation
        normalized_data = {
            "entries": [(e.registration_no, e.label) for e in sorted_entries],
            "winners_to_pick": winners_to_pick,
            "seed": seed
        }
        
        # Serialize to JSON with consistent ordering
        json_str = json.dumps(normalized_data, sort_keys=True, separators=(',', ':'))
        
        # Compute SHA256
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def shuffle(self) -> List[str]:
        """Shuffle the entries and freeze the draw sequence.
        
        This method must be called before any winners can be picked. It uses
        either deterministic shuffling (if seed provided) or cryptographically
        secure shuffling (if no seed).
        
        Returns:
            List of registration numbers in shuffled order.
        
        Raises:
            LotteryError: If the draw has already been shuffled.
        """
        if self._status != "Draft":
            raise LotteryError("Draw has already been shuffled")
        
        # Create list of registration numbers to shuffle
        reg_numbers = [entry.registration_no for entry in self._original_entries]
        
        if self._seed is not None:
            # Deterministic shuffle using seeded random
            rng = random.Random(self._seed)
            rng.shuffle(reg_numbers)
        else:
            # Cryptographically secure shuffle
            # Use secrets.SystemRandom for cryptographic security
            crypto_rng = secrets.SystemRandom()
            crypto_rng.shuffle(reg_numbers)
        
        self._shuffled_sequence = reg_numbers
        self._status = "Shuffled"
        
        return list(self._shuffled_sequence)  # Return immutable copy
    
    def pick_next(self) -> Winner:
        """Pick the next winner from the shuffled sequence.
        
        Winners are selected in the order determined by the shuffle.
        Each winner is assigned a rank (1-based) and timestamp.
        
        Returns:
            Winner object with registration_no, rank, and picked_at timestamp.
        
        Raises:
            LotteryError: If draw hasn't been shuffled, if all winners have
                         been picked, or if attempting to pick beyond the limit.
        """
        if self._status == "Draft":
            raise LotteryError("Must shuffle before picking winners")
        if self._status == "Completed":
            raise LotteryError("All winners have already been picked")
        if len(self._winners) >= self._winners_to_pick:
            raise LotteryError("Cannot pick more winners than specified limit")
        if self._current_position >= len(self._shuffled_sequence):
            raise LotteryError("No more entries available to pick from")
        
        # Get next registration number from shuffled sequence
        reg_no = self._shuffled_sequence[self._current_position]
        
        # Create winner with current timestamp
        rank = len(self._winners) + 1
        winner = Winner(
            registration_no=reg_no,
            rank=rank,
            picked_at=datetime.now()
        )
        
        # Update state
        self._winners.append(winner)
        self._current_position += 1
        
        # Check if we've completed the draw
        if len(self._winners) == self._winners_to_pick:
            self._status = "Completed"
        
        return winner
    
    def state(self) -> DrawState:
        """Get the current state of the lottery draw.
        
        Returns an immutable snapshot of the draw state including winners,
        remaining entries, counts, status, and audit information.
        
        Returns:
            DrawState object representing current state.
        """
        # Calculate remaining entries
        picked_reg_nos = {winner.registration_no for winner in self._winners}
        
        if self._status == "Draft":
            # Before shuffle, all entries are remaining
            remaining = [entry.registration_no for entry in self._original_entries]
        else:
            # After shuffle, remaining are those not yet picked from shuffled sequence
            remaining = [
                reg_no for reg_no in self._shuffled_sequence[self._current_position:]
                if reg_no not in picked_reg_nos
            ]
        
        return DrawState(
            winners=list(self._winners),  # Immutable copy
            remaining=remaining,
            picked_count=len(self._winners),
            total=len(self._original_entries),
            winners_to_pick=self._winners_to_pick,
            status=self._status,
            input_hash=self._input_hash
        )
    
    def export_csv(self) -> str:
        """Export the current draw state to CSV format.
        
        The CSV contains all winners followed by remaining entries in their
        canonical order. Winners include their rank and timestamp, while
        remaining entries show their position in the shuffled sequence.
        
        Returns:
            UTF-8 encoded CSV string with headers:
            registration_no,status,rank,picked_at,position_in_sequence
        
        Raises:
            LotteryError: If the draw hasn't been shuffled yet.
        """
        if self._status == "Draft":
            raise LotteryError("Cannot export CSV before shuffling")
        
        # Use StringIO to build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'registration_no',
            'status',
            'rank',
            'picked_at',
            'position_in_sequence'
        ])
        
        # Write winners
        for winner in self._winners:
            writer.writerow([
                winner.registration_no,
                'winner',
                winner.rank,
                winner.picked_at.isoformat(),
                self._shuffled_sequence.index(winner.registration_no) + 1
            ])
        
        # Write remaining entries
        for i, reg_no in enumerate(self._shuffled_sequence[self._current_position:], 
                                   start=self._current_position + 1):
            writer.writerow([
                reg_no,
                'remaining',
                '',  # No rank for non-winners
                '',  # No timestamp for non-winners
                i
            ])
        
        return output.getvalue()