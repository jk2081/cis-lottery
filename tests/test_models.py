"""Tests for lottery_engine.models module."""

import pytest
from datetime import datetime
from lottery_engine.models import Entry, Winner, DrawState, LotteryError


class TestEntry:
    """Test cases for the Entry dataclass."""
    
    def test_entry_creation_with_label(self):
        """Test creating an entry with both registration_no and label."""
        entry = Entry("REG001", "John Doe")
        assert entry.registration_no == "REG001"
        assert entry.label == "John Doe"
    
    def test_entry_creation_without_label(self):
        """Test creating an entry with only registration_no."""
        entry = Entry("REG001")
        assert entry.registration_no == "REG001"
        assert entry.label is None
    
    def test_entry_empty_registration_no(self):
        """Test that empty registration_no raises an error."""
        with pytest.raises(LotteryError, match="Registration number cannot be empty"):
            Entry("")
    
    def test_entry_immutability(self):
        """Test that Entry objects are immutable."""
        entry = Entry("REG001", "John Doe")
        with pytest.raises(AttributeError):
            entry.registration_no = "REG002"  # type: ignore
    
    def test_entry_equality(self):
        """Test that entries with same data are equal."""
        entry1 = Entry("REG001", "John Doe")
        entry2 = Entry("REG001", "John Doe")
        entry3 = Entry("REG002", "John Doe")
        
        assert entry1 == entry2
        assert entry1 != entry3


class TestWinner:
    """Test cases for the Winner dataclass."""
    
    def test_winner_creation(self):
        """Test creating a winner with all required fields."""
        timestamp = datetime.now()
        winner = Winner("REG001", 1, timestamp)
        
        assert winner.registration_no == "REG001"
        assert winner.rank == 1
        assert winner.picked_at == timestamp
    
    def test_winner_empty_registration_no(self):
        """Test that empty registration_no raises an error."""
        with pytest.raises(LotteryError, match="Registration number cannot be empty"):
            Winner("", 1, datetime.now())
    
    def test_winner_invalid_rank(self):
        """Test that non-positive rank raises an error."""
        with pytest.raises(LotteryError, match="Rank must be positive"):
            Winner("REG001", 0, datetime.now())
        
        with pytest.raises(LotteryError, match="Rank must be positive"):
            Winner("REG001", -1, datetime.now())
    
    def test_winner_immutability(self):
        """Test that Winner objects are immutable."""
        winner = Winner("REG001", 1, datetime.now())
        with pytest.raises(AttributeError):
            winner.rank = 2  # type: ignore


class TestDrawState:
    """Test cases for the DrawState dataclass."""
    
    def test_draw_state_creation(self):
        """Test creating a valid draw state."""
        winners = [Winner("REG001", 1, datetime.now())]
        remaining = ["REG002", "REG003"]
        
        state = DrawState(
            winners=winners,
            remaining=remaining,
            picked_count=1,
            total=3,
            winners_to_pick=2,
            status="Shuffled",
            input_hash="abc123"
        )
        
        assert len(state.winners) == 1
        assert len(state.remaining) == 2
        assert state.picked_count == 1
        assert state.total == 3
        assert state.winners_to_pick == 2
        assert state.status == "Shuffled"
        assert state.input_hash == "abc123"
    
    def test_draw_state_negative_picked_count(self):
        """Test that negative picked_count raises an error."""
        with pytest.raises(LotteryError, match="Picked count cannot be negative"):
            DrawState([], [], -1, 3, 2, "Draft", "abc123")
    
    def test_draw_state_negative_total(self):
        """Test that negative total raises an error."""
        with pytest.raises(LotteryError, match="Total entries cannot be negative"):
            DrawState([], [], 0, -1, 2, "Draft", "abc123")
    
    def test_draw_state_invalid_winners_to_pick(self):
        """Test that non-positive winners_to_pick raises an error."""
        with pytest.raises(LotteryError, match="Winners to pick must be positive"):
            DrawState([], [], 0, 3, 0, "Draft", "abc123")
    
    def test_draw_state_too_many_winners_to_pick(self):
        """Test that winners_to_pick > total raises an error."""
        with pytest.raises(LotteryError, match="Cannot pick more winners than total entries"):
            DrawState([], [], 0, 3, 5, "Draft", "abc123")
    
    def test_draw_state_winners_count_mismatch(self):
        """Test that winners list length must match picked_count."""
        winners = [Winner("REG001", 1, datetime.now())]
        
        with pytest.raises(LotteryError, match="Winners list length must match picked count"):
            DrawState(winners, [], 2, 3, 2, "Draft", "abc123")  # 1 winner but picked_count=2
    
    def test_draw_state_invalid_status(self):
        """Test that invalid status raises an error."""
        with pytest.raises(LotteryError, match="Invalid status"):
            DrawState([], [], 0, 3, 2, "InvalidStatus", "abc123")
    
    def test_draw_state_empty_input_hash(self):
        """Test that empty input_hash raises an error."""
        with pytest.raises(LotteryError, match="Input hash cannot be empty"):
            DrawState([], [], 0, 3, 2, "Draft", "")
    
    def test_draw_state_valid_statuses(self):
        """Test that all valid statuses are accepted."""
        for status in ("Draft", "Shuffled", "Completed"):
            state = DrawState([], [], 0, 3, 2, status, "abc123")
            assert state.status == status
    
    def test_draw_state_immutability(self):
        """Test that DrawState objects are immutable."""
        state = DrawState([], [], 0, 3, 2, "Draft", "abc123")
        with pytest.raises(AttributeError):
            state.picked_count = 1  # type: ignore


class TestLotteryError:
    """Test cases for the LotteryError exception."""
    
    def test_lottery_error_creation(self):
        """Test creating and raising LotteryError."""
        error_msg = "Test error message"
        
        with pytest.raises(LotteryError, match=error_msg):
            raise LotteryError(error_msg)
    
    def test_lottery_error_inheritance(self):
        """Test that LotteryError inherits from Exception."""
        error = LotteryError("test")
        assert isinstance(error, Exception)