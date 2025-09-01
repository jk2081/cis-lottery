"""Integration tests for lottery_engine package."""

import pytest
from datetime import datetime

from lottery_engine import Entry, LotteryDraw, Winner, DrawState, LotteryError


class TestEndToEndFlow:
    """Test complete end-to-end lottery flows."""
    
    def test_complete_seeded_lottery_flow(self):
        """Test complete lottery flow with seeded randomization."""
        # Prepare entries
        entries = [Entry(str(i)) for i in range(1, 96)]  # 95 entries as in PRD example
        
        # Create draw (40 winners from 95 entries)
        draw = LotteryDraw(entries=entries, winners_to_pick=40, seed="my-secret-seed")
        
        # Initial state should be Draft
        initial_state = draw.state()
        assert initial_state.status == "Draft"
        assert initial_state.picked_count == 0
        assert len(initial_state.winners) == 0
        assert len(initial_state.remaining) == 95
        
        # Shuffle (freeze sequence)
        shuffled_sequence = draw.shuffle()
        assert len(shuffled_sequence) == 95
        assert set(shuffled_sequence) == {str(i) for i in range(1, 96)}
        
        # State after shuffle
        shuffled_state = draw.state()
        assert shuffled_state.status == "Shuffled"
        assert shuffled_state.picked_count == 0
        
        # Reveal winners one by one
        winners = []
        for i in range(40):
            winner = draw.pick_next()
            winners.append(winner)
            
            assert winner.rank == i + 1
            assert isinstance(winner.picked_at, datetime)
            assert winner.registration_no in shuffled_sequence
        
        # Final state should be Completed
        final_state = draw.state()
        assert final_state.status == "Completed"
        assert final_state.picked_count == 40
        assert len(final_state.winners) == 40
        assert len(final_state.remaining) == 55
        
        # Export to CSV
        csv_text = draw.export_csv()
        assert csv_text is not None
        assert len(csv_text) > 0
        
        # CSV should contain all entries
        lines = csv_text.strip().split('\n')
        assert len(lines) == 96  # 1 header + 95 entries
    
    def test_reproducible_lottery_with_same_seed(self):
        """Test that same seed produces identical results."""
        entries = [Entry(str(i)) for i in range(1, 21)]  # 20 entries
        seed = "reproducible-test"
        
        # Run first lottery
        draw1 = LotteryDraw(entries=entries, winners_to_pick=5, seed=seed)
        sequence1 = draw1.shuffle()
        winners1 = []
        for _ in range(5):
            winners1.append(draw1.pick_next())
        
        # Run second lottery with same parameters
        draw2 = LotteryDraw(entries=entries, winners_to_pick=5, seed=seed)
        sequence2 = draw2.shuffle()
        winners2 = []
        for _ in range(5):
            winners2.append(draw2.pick_next())
        
        # Results should be identical
        assert sequence1 == sequence2
        assert len(winners1) == len(winners2)
        for w1, w2 in zip(winners1, winners2):
            assert w1.registration_no == w2.registration_no
            assert w1.rank == w2.rank
        
        # Input hashes should be identical
        assert draw1.state().input_hash == draw2.state().input_hash
    
    def test_cryptographic_lottery_uniqueness(self):
        """Test that unseeded lotteries produce different results."""
        entries = [Entry(str(i)) for i in range(1, 101)]  # 100 entries
        
        # Run multiple unseeded lotteries
        results = []
        for _ in range(5):
            draw = LotteryDraw(entries=entries, winners_to_pick=10)  # No seed
            sequence = draw.shuffle()
            results.append(sequence)
        
        # All results should be different (extremely high probability)
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], i+1):
                assert result1 != result2, f"Results {i} and {j} should be different"
    
    def test_audit_integrity_with_input_hash(self):
        """Test audit integrity using input hash."""
        entries = [Entry("A"), Entry("B"), Entry("C")]
        
        # Create multiple draws with same parameters
        draw1 = LotteryDraw(entries, 2, "audit-test")
        draw2 = LotteryDraw(entries, 2, "audit-test")
        
        # Input hashes should be identical
        hash1 = draw1.state().input_hash
        hash2 = draw2.state().input_hash
        assert hash1 == hash2
        
        # Different parameters should produce different hashes
        draw3 = LotteryDraw(entries, 1, "audit-test")  # Different winners_to_pick
        hash3 = draw3.state().input_hash
        assert hash1 != hash3
        
        draw4 = LotteryDraw(entries, 2, "different-seed")  # Different seed
        hash4 = draw4.state().input_hash
        assert hash1 != hash4
    
    def test_partial_winner_selection_and_resume(self):
        """Test picking some winners, checking state, then continuing."""
        entries = [Entry(str(i)) for i in range(1, 11)]  # 10 entries
        draw = LotteryDraw(entries, 5, "partial-test")
        draw.shuffle()
        
        # Pick first 2 winners
        winner1 = draw.pick_next()
        winner2 = draw.pick_next()
        
        # Check intermediate state
        state = draw.state()
        assert state.status == "Shuffled"  # Not completed yet
        assert state.picked_count == 2
        assert len(state.winners) == 2
        assert len(state.remaining) == 8
        
        # Continue picking remaining winners
        winner3 = draw.pick_next()
        winner4 = draw.pick_next()
        winner5 = draw.pick_next()
        
        # Check final state
        final_state = draw.state()
        assert final_state.status == "Completed"
        assert final_state.picked_count == 5
        assert len(final_state.winners) == 5
        assert len(final_state.remaining) == 5
        
        # All winners should have unique registration numbers and sequential ranks
        reg_nos = [w.registration_no for w in final_state.winners]
        ranks = [w.rank for w in final_state.winners]
        
        assert len(set(reg_nos)) == 5  # All unique
        assert ranks == [1, 2, 3, 4, 5]  # Sequential ranks
    
    def test_edge_case_single_entry_single_winner(self):
        """Test edge case with single entry and single winner."""
        entries = [Entry("ONLY_ONE")]
        draw = LotteryDraw(entries, 1, "single")
        
        draw.shuffle()
        winner = draw.pick_next()
        
        assert winner.registration_no == "ONLY_ONE"
        assert winner.rank == 1
        
        state = draw.state()
        assert state.status == "Completed"
        assert state.picked_count == 1
        assert state.total == 1
        assert len(state.remaining) == 0
    
    def test_edge_case_all_entries_as_winners(self):
        """Test edge case where all entries become winners."""
        entries = [Entry(str(i)) for i in range(1, 6)]  # 5 entries
        draw = LotteryDraw(entries, 5, "all-winners")  # All become winners
        
        draw.shuffle()
        
        winners = []
        for i in range(5):
            winner = draw.pick_next()
            winners.append(winner)
            assert winner.rank == i + 1
        
        # Final state
        state = draw.state()
        assert state.status == "Completed"
        assert state.picked_count == 5
        assert state.total == 5
        assert len(state.remaining) == 0
        
        # All original entries should be winners
        winner_reg_nos = {w.registration_no for w in winners}
        original_reg_nos = {e.registration_no for e in entries}
        assert winner_reg_nos == original_reg_nos


class TestErrorHandlingIntegration:
    """Test error handling in integrated scenarios."""
    
    def test_invalid_flow_sequence_errors(self):
        """Test errors when operations are performed out of sequence."""
        entries = [Entry("1"), Entry("2"), Entry("3")]
        draw = LotteryDraw(entries, 2)
        
        # Try to pick before shuffle
        with pytest.raises(LotteryError, match="Must shuffle before picking winners"):
            draw.pick_next()
        
        # Try to export CSV before shuffle
        with pytest.raises(LotteryError, match="Cannot export CSV before shuffling"):
            draw.export_csv()
        
        # Now shuffle
        draw.shuffle()
        
        # Pick all available winners
        draw.pick_next()
        draw.pick_next()
        
        # Try to pick more than available
        with pytest.raises(LotteryError, match="All winners have already been picked"):
            draw.pick_next()
    
    def test_concurrent_lottery_independence(self):
        """Test that multiple concurrent lotteries don't interfere."""
        entries1 = [Entry("A"), Entry("B"), Entry("C")]
        entries2 = [Entry("X"), Entry("Y"), Entry("Z")]
        
        draw1 = LotteryDraw(entries1, 2, "lottery1")
        draw2 = LotteryDraw(entries2, 1, "lottery2")
        
        # Shuffle both
        seq1 = draw1.shuffle()
        seq2 = draw2.shuffle()
        
        # Pick winners from both
        winner1_1 = draw1.pick_next()
        winner2_1 = draw2.pick_next()
        winner1_2 = draw1.pick_next()
        
        # Check they don't interfere
        assert winner1_1.registration_no in ["A", "B", "C"]
        assert winner1_2.registration_no in ["A", "B", "C"]
        assert winner2_1.registration_no in ["X", "Y", "Z"]
        
        assert winner1_1.rank == 1
        assert winner1_2.rank == 2
        assert winner2_1.rank == 1


class TestSpecialCharactersAndUnicode:
    """Test handling of special characters and Unicode in registration numbers."""
    
    def test_unicode_registration_numbers(self):
        """Test lottery with Unicode registration numbers."""
        entries = [
            Entry("测试1", "Chinese Test"),
            Entry("тест2", "Russian Test"), 
            Entry("🎲3", "Emoji Test"),
            Entry("café4", "Accent Test")
        ]
        
        draw = LotteryDraw(entries, 2, "unicode-test")
        draw.shuffle()
        
        winner1 = draw.pick_next()
        winner2 = draw.pick_next()
        
        # Winners should have valid Unicode registration numbers
        assert winner1.registration_no in ["测试1", "тест2", "🎲3", "café4"]
        assert winner2.registration_no in ["测试1", "тест2", "🎲3", "café4"]
        assert winner1.registration_no != winner2.registration_no
        
        # CSV export should handle Unicode correctly
        csv_output = draw.export_csv()
        assert "测试1" in csv_output or "тест2" in csv_output or "🎲3" in csv_output or "café4" in csv_output
    
    def test_special_characters_in_labels(self):
        """Test entries with special characters in labels."""
        entries = [
            Entry("1", "Name with \"quotes\""),
            Entry("2", "Name with, commas"),
            Entry("3", "Name with\nnewlines"),
            Entry("4", "Name with\ttabs")
        ]
        
        draw = LotteryDraw(entries, 4, "special-chars")
        draw.shuffle()
        
        # Should handle all entries correctly
        for _ in range(4):
            winner = draw.pick_next()
            assert winner.registration_no in ["1", "2", "3", "4"]
        
        # CSV export should handle special characters in labels
        csv_output = draw.export_csv()
        assert len(csv_output) > 0  # Should not crash