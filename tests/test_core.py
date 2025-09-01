"""Tests for lottery_engine.core module."""

import csv
import io
import pytest
from datetime import datetime
from unittest.mock import patch

from lottery_engine.core import LotteryDraw
from lottery_engine.models import Entry, Winner, LotteryError


class TestLotteryDrawInitialization:
    """Test cases for LotteryDraw initialization."""
    
    def test_init_valid_params(self):
        """Test initializing with valid parameters."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 2)
        
        assert draw._winners_to_pick == 2
        assert len(draw._original_entries) == 3
        assert draw._status == "Draft"
        assert len(draw._winners) == 0
    
    def test_init_with_seed(self):
        """Test initializing with a seed."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 1, "test-seed")
        
        assert draw._seed == "test-seed"
    
    def test_init_empty_entries(self):
        """Test that empty entries list raises an error."""
        with pytest.raises(LotteryError, match="Entries list cannot be empty"):
            LotteryDraw([], 1)
    
    def test_init_invalid_winners_count(self):
        """Test that non-positive winners_to_pick raises an error."""
        entries = [Entry("1"), Entry("2")]
        
        with pytest.raises(LotteryError, match="Winners to pick must be positive"):
            LotteryDraw(entries, 0)
        
        with pytest.raises(LotteryError, match="Winners to pick must be positive"):
            LotteryDraw(entries, -1)
    
    def test_init_too_many_winners(self):
        """Test that winners_to_pick > entries raises an error."""
        entries = [Entry("1"), Entry("2")]
        
        with pytest.raises(LotteryError, match="Cannot pick more winners than available entries"):
            LotteryDraw(entries, 3)
    
    def test_init_duplicate_registration_numbers(self):
        """Test that duplicate registration numbers raise an error."""
        entries = [Entry("1"), Entry("1"), Entry("2")]
        
        with pytest.raises(LotteryError, match="All entries must have unique registration numbers"):
            LotteryDraw(entries, 2)


class TestInputHashComputation:
    """Test cases for input hash computation."""
    
    def test_input_hash_deterministic(self):
        """Test that input hash is deterministic for same inputs."""
        entries = [Entry("1", "A"), Entry("2", "B")]
        
        draw1 = LotteryDraw(entries, 1, "seed")
        draw2 = LotteryDraw(entries, 1, "seed")
        
        assert draw1._input_hash == draw2._input_hash
    
    def test_input_hash_different_entries(self):
        """Test that different entries produce different hashes."""
        entries1 = [Entry("1"), Entry("2")]
        entries2 = [Entry("3"), Entry("4")]
        
        draw1 = LotteryDraw(entries1, 1)
        draw2 = LotteryDraw(entries2, 1)
        
        assert draw1._input_hash != draw2._input_hash
    
    def test_input_hash_different_winners_count(self):
        """Test that different winners_to_pick produces different hashes."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        
        draw1 = LotteryDraw(entries, 1)
        draw2 = LotteryDraw(entries, 2)
        
        assert draw1._input_hash != draw2._input_hash
    
    def test_input_hash_different_seed(self):
        """Test that different seeds produce different hashes."""
        entries = [Entry("1"), Entry("2")]
        
        draw1 = LotteryDraw(entries, 1, "seed1")
        draw2 = LotteryDraw(entries, 1, "seed2")
        
        assert draw1._input_hash != draw2._input_hash
    
    def test_input_hash_entry_order_independence(self):
        """Test that entry order doesn't affect hash (normalized)."""
        entries1 = [Entry("1"), Entry("2"), Entry("3")]
        entries2 = [Entry("3"), Entry("1"), Entry("2")]
        
        draw1 = LotteryDraw(entries1, 2, "seed")
        draw2 = LotteryDraw(entries2, 2, "seed")
        
        assert draw1._input_hash == draw2._input_hash


class TestShuffle:
    """Test cases for shuffle functionality."""
    
    def test_shuffle_deterministic(self):
        """Test that shuffle with seed is deterministic."""
        entries = [Entry(str(i)) for i in range(100)]
        
        draw1 = LotteryDraw(entries, 10, "test-seed")
        draw2 = LotteryDraw(entries, 10, "test-seed")
        
        sequence1 = draw1.shuffle()
        sequence2 = draw2.shuffle()
        
        assert sequence1 == sequence2
    
    def test_shuffle_different_seeds(self):
        """Test that different seeds produce different shuffles."""
        entries = [Entry(str(i)) for i in range(100)]
        
        draw1 = LotteryDraw(entries, 10, "seed1")
        draw2 = LotteryDraw(entries, 10, "seed2")
        
        sequence1 = draw1.shuffle()
        sequence2 = draw2.shuffle()
        
        # With 100 entries, extremely unlikely to be the same
        assert sequence1 != sequence2
    
    def test_shuffle_cryptographic_different(self):
        """Test that cryptographic shuffles are different (high probability)."""
        entries = [Entry(str(i)) for i in range(100)]
        
        draw1 = LotteryDraw(entries, 10)  # No seed
        draw2 = LotteryDraw(entries, 10)  # No seed
        
        sequence1 = draw1.shuffle()
        sequence2 = draw2.shuffle()
        
        # With 100 entries, extremely unlikely to be the same
        assert sequence1 != sequence2
    
    def test_shuffle_contains_all_entries(self):
        """Test that shuffle contains all original entries."""
        entries = [Entry(str(i)) for i in range(10)]
        draw = LotteryDraw(entries, 5, "seed")
        
        shuffled = draw.shuffle()
        
        assert len(shuffled) == 10
        assert set(shuffled) == {str(i) for i in range(10)}
    
    def test_shuffle_changes_status(self):
        """Test that shuffle changes status to Shuffled."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 1)
        
        assert draw._status == "Draft"
        draw.shuffle()
        assert draw._status == "Shuffled"
    
    def test_shuffle_already_shuffled(self):
        """Test that shuffling again raises an error."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 1)
        
        draw.shuffle()
        
        with pytest.raises(LotteryError, match="Draw has already been shuffled"):
            draw.shuffle()


class TestPickNext:
    """Test cases for pick_next functionality."""
    
    def test_pick_next_before_shuffle(self):
        """Test that picking before shuffle raises an error."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 1)
        
        with pytest.raises(LotteryError, match="Must shuffle before picking winners"):
            draw.pick_next()
    
    def test_pick_next_basic(self):
        """Test basic winner picking."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 2, "seed")
        draw.shuffle()
        
        winner1 = draw.pick_next()
        
        assert isinstance(winner1, Winner)
        assert winner1.registration_no in ["1", "2", "3"]
        assert winner1.rank == 1
        assert isinstance(winner1.picked_at, datetime)
    
    def test_pick_next_multiple_winners(self):
        """Test picking multiple winners."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 3, "seed")
        draw.shuffle()
        
        winner1 = draw.pick_next()
        winner2 = draw.pick_next()
        winner3 = draw.pick_next()
        
        # Check ranks are sequential
        assert winner1.rank == 1
        assert winner2.rank == 2
        assert winner3.rank == 3
        
        # Check all different registration numbers
        reg_nos = {winner1.registration_no, winner2.registration_no, winner3.registration_no}
        assert len(reg_nos) == 3
        assert reg_nos == {"1", "2", "3"}
    
    def test_pick_next_deterministic_order(self):
        """Test that pick order is deterministic with same seed."""
        entries = [Entry(str(i)) for i in range(10)]
        
        draw1 = LotteryDraw(entries, 5, "seed")
        draw1.shuffle()
        
        draw2 = LotteryDraw(entries, 5, "seed")
        draw2.shuffle()
        
        winners1 = [draw1.pick_next().registration_no for _ in range(5)]
        winners2 = [draw2.pick_next().registration_no for _ in range(5)]
        
        assert winners1 == winners2
    
    def test_pick_next_exceeds_limit(self):
        """Test that picking beyond limit raises an error."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 1, "seed")
        draw.shuffle()
        
        draw.pick_next()  # Pick first winner
        
        with pytest.raises(LotteryError, match="Cannot pick more winners than specified limit"):
            draw.pick_next()  # Try to pick second winner
    
    def test_pick_next_status_completed(self):
        """Test that status changes to Completed when all winners picked."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 2, "seed")
        draw.shuffle()
        
        assert draw._status == "Shuffled"
        
        draw.pick_next()
        assert draw._status == "Shuffled"  # Still shuffled
        
        draw.pick_next()
        assert draw._status == "Completed"  # Now completed
    
    def test_pick_next_after_completed(self):
        """Test that picking after completion raises an error."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 1, "seed")
        draw.shuffle()
        
        draw.pick_next()  # Complete the draw
        
        with pytest.raises(LotteryError, match="All winners have already been picked"):
            draw.pick_next()


class TestState:
    """Test cases for state() method."""
    
    def test_state_draft(self):
        """Test state in Draft status."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 2)
        
        state = draw.state()
        
        assert state.winners == []
        assert set(state.remaining) == {"1", "2", "3"}
        assert state.picked_count == 0
        assert state.total == 3
        assert state.winners_to_pick == 2
        assert state.status == "Draft"
        assert state.input_hash is not None
    
    def test_state_shuffled(self):
        """Test state after shuffle."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 2, "seed")
        draw.shuffle()
        
        state = draw.state()
        
        assert state.winners == []
        assert len(state.remaining) == 3
        assert state.picked_count == 0
        assert state.status == "Shuffled"
    
    def test_state_with_winners(self):
        """Test state with some winners picked."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 3, "seed")
        draw.shuffle()
        
        winner1 = draw.pick_next()
        winner2 = draw.pick_next()
        
        state = draw.state()
        
        assert len(state.winners) == 2
        assert state.winners[0] == winner1
        assert state.winners[1] == winner2
        assert len(state.remaining) == 1
        assert state.picked_count == 2
        assert state.status == "Shuffled"
    
    def test_state_completed(self):
        """Test state when draw is completed."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 2, "seed")
        draw.shuffle()
        
        draw.pick_next()
        draw.pick_next()
        
        state = draw.state()
        
        assert len(state.winners) == 2
        assert state.remaining == []
        assert state.picked_count == 2
        assert state.status == "Completed"


class TestExportCSV:
    """Test cases for export_csv() method."""
    
    def test_export_csv_before_shuffle(self):
        """Test that exporting CSV before shuffle raises an error."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 1)
        
        with pytest.raises(LotteryError, match="Cannot export CSV before shuffling"):
            draw.export_csv()
    
    def test_export_csv_after_shuffle_no_winners(self):
        """Test CSV export after shuffle but before picking winners."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 2, "test-seed")
        draw.shuffle()
        
        csv_output = draw.export_csv()
        
        # Parse CSV to verify format
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 3  # All entries are remaining
        
        # Check headers
        expected_headers = ['registration_no', 'status', 'rank', 'picked_at', 'position_in_sequence']
        assert reader.fieldnames == expected_headers
        
        # All should be 'remaining' status
        for row in rows:
            assert row['status'] == 'remaining'
            assert row['rank'] == ''
            assert row['picked_at'] == ''
            assert int(row['position_in_sequence']) > 0
    
    def test_export_csv_with_winners(self):
        """Test CSV export with some winners picked."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 2, "test-seed")
        draw.shuffle()
        
        winner1 = draw.pick_next()
        
        csv_output = draw.export_csv()
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 3
        
        # Find winner row
        winner_rows = [row for row in rows if row['status'] == 'winner']
        remaining_rows = [row for row in rows if row['status'] == 'remaining']
        
        assert len(winner_rows) == 1
        assert len(remaining_rows) == 2
        
        # Check winner row
        winner_row = winner_rows[0]
        assert winner_row['registration_no'] == winner1.registration_no
        assert winner_row['rank'] == str(winner1.rank)
        assert winner_row['picked_at'] != ''
        assert int(winner_row['position_in_sequence']) > 0
    
    def test_export_csv_completed_draw(self):
        """Test CSV export for completed draw."""
        entries = [Entry("1"), Entry("2")]
        draw = LotteryDraw(entries, 2, "test-seed")
        draw.shuffle()
        
        winner1 = draw.pick_next()
        winner2 = draw.pick_next()
        
        csv_output = draw.export_csv()
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        assert len(rows) == 2
        
        # All should be winners
        for row in rows:
            assert row['status'] == 'winner'
            assert row['rank'] in ['1', '2']
            assert row['picked_at'] != ''
    
    def test_export_csv_utf8_encoding(self):
        """Test that CSV export handles UTF-8 characters correctly."""
        entries = [Entry("测试1"), Entry("测试2")]
        draw = LotteryDraw(entries, 1, "seed")
        draw.shuffle()
        
        csv_output = draw.export_csv()
        
        # Should not raise encoding errors
        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)
        
        reg_nos = [row['registration_no'] for row in rows]
        assert "测试1" in reg_nos
        assert "测试2" in reg_nos


class TestPerformance:
    """Test cases for performance requirements."""
    
    def test_large_dataset_performance(self):
        """Test performance with large dataset (100k entries)."""
        # Create 100k entries
        entries = [Entry(str(i)) for i in range(100_000)]
        
        # This should complete without noticeable delay
        draw = LotteryDraw(entries, 1000, "performance-test")
        
        # Shuffle should be fast
        shuffled = draw.shuffle()
        assert len(shuffled) == 100_000
        
        # Picking winners should be fast
        for _ in range(1000):
            winner = draw.pick_next()
            assert isinstance(winner, Winner)
        
        # State export should be fast
        state = draw.state()
        assert state.picked_count == 1000
        
        # CSV export should be fast
        csv_output = draw.export_csv()
        assert len(csv_output) > 0