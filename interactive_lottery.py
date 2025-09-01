#!/usr/bin/env python3
"""Interactive lottery draw script.

Run this script in your terminal to experience an interactive lottery
where you press Enter to reveal each winner one by one.

Usage:
    python3 interactive_lottery.py                    # Use default 50 random entries
    python3 interactive_lottery.py entries.csv        # Load from CSV file
    python3 interactive_lottery.py entries.csv --random    # Force random mode
    python3 interactive_lottery.py entries.csv --reproducible  # Force reproducible mode

CSV File Format:
    First line: number_of_winners
    Following lines: one registration_number per line
    
Example CSV:
    15
    REG-001
    REG-002
    REG-003
    ...
"""

import sys
import csv
import random
from pathlib import Path
from lottery_engine import Entry, LotteryDraw


def load_entries_from_csv(csv_file):
    """Load entries and winner count from CSV file.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        tuple: (entries_list, winners_to_pick)
        
    Raises:
        ValueError: If file format is invalid
        FileNotFoundError: If file doesn't exist
    """
    csv_path = Path(csv_file)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if len(lines) < 2:
        raise ValueError("CSV file must contain at least 2 lines (winners count + entries)")
    
    # First line should be the number of winners
    try:
        winners_to_pick = int(lines[0])
    except ValueError:
        raise ValueError(f"First line must be a number (winners to pick), got: {lines[0]}")
    
    if winners_to_pick <= 0:
        raise ValueError(f"Number of winners must be positive, got: {winners_to_pick}")
    
    # Remaining lines are registration numbers
    reg_numbers = lines[1:]
    
    if len(reg_numbers) == 0:
        raise ValueError("No registration numbers found in CSV file")
    
    if winners_to_pick > len(reg_numbers):
        raise ValueError(f"Cannot pick {winners_to_pick} winners from {len(reg_numbers)} entries")
    
    # Validate registration numbers are not empty and unique
    seen_numbers = set()
    valid_reg_numbers = []
    
    for i, reg_no in enumerate(reg_numbers, 2):  # Start from line 2
        if not reg_no:
            raise ValueError(f"Empty registration number on line {i}")
        
        if reg_no in seen_numbers:
            raise ValueError(f"Duplicate registration number on line {i}: {reg_no}")
        
        seen_numbers.add(reg_no)
        valid_reg_numbers.append(reg_no)
    
    # Create Entry objects
    entries = [Entry(reg_no) for reg_no in valid_reg_numbers]
    
    return entries, winners_to_pick


def generate_default_entries():
    """Generate default 50 random entries for demonstration."""
    random.seed(42)  # For reproducible random numbers
    reg_numbers = []
    used_numbers = set()

    while len(reg_numbers) < 50:
        num = random.randint(1000, 9999)
        if num not in used_numbers:
            reg_numbers.append(f"REG-{num}")
            used_numbers.add(num)

    entries = [Entry(reg_no) for reg_no in sorted(reg_numbers)]
    return entries, 15


def main():
    print("🎲 Interactive Lottery Draw")
    print("=" * 40)

    # Parse command line arguments
    force_mode = None
    csv_file = None
    
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--random":
            force_mode = "random"
        elif arg == "--reproducible":
            force_mode = "reproducible"
        elif not arg.startswith("--"):
            csv_file = arg

    # Check if CSV file is provided as command line argument
    if csv_file:
        print(f"📁 Loading entries from: {csv_file}")
        
        try:
            entries, winners_to_pick = load_entries_from_csv(csv_file)
            print(f"✅ Loaded {len(entries)} entries from CSV file")
            print(f"🎯 Ready to draw {winners_to_pick} winners!")
            
            # Show some sample entries
            print(f"\n📝 Entries loaded:")
            print(f"   First: {entries[0].registration_no}")
            print(f"   Last:  {entries[-1].registration_no}")
            if len(entries) > 10:
                print(f"   Sample: {', '.join([e.registration_no for e in entries[1:6]])}")
                print(f"   ... (and {len(entries)-6} more)")
            else:
                print(f"   All: {', '.join([e.registration_no for e in entries])}")
                
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ Error loading CSV file: {e}")
            print("\n💡 CSV file format should be:")
            print("   Line 1: number_of_winners")
            print("   Line 2+: registration_numbers (one per line)")
            print(f"\n   Example:")
            print(f"   15")
            print(f"   REG-001")
            print(f"   REG-002")
            print(f"   ...")
            return
            
    else:
        # Use default random entries
        print("📋 No CSV file provided, using default random entries")
        entries, winners_to_pick = generate_default_entries()
        
        print(f"📋 Generated {len(entries)} entries from {entries[0].registration_no} to {entries[-1].registration_no}")
        print(f"🎯 Ready to draw {winners_to_pick} winners!")
        
        # Show some sample entries
        print("\n📝 Sample entries:")
        for i in range(0, min(10, len(entries)), 2):
            if i+1 < len(entries):
                print(f"   {entries[i].registration_no}  {entries[i+1].registration_no}")
            else:
                print(f"   {entries[i].registration_no}")
        if len(entries) > 10:
            print(f"   ... (and {len(entries)-10} more)")

    # Determine randomization mode
    if force_mode:
        # Mode forced via command line
        if force_mode == "reproducible":
            seed = "reproducible-draw"
            print("🔒 Using reproducible mode (forced via --reproducible)")
        else:
            seed = None
            print("🎲 Using random mode (forced via --random)")
    else:
        # Ask user about randomization preference
        print(f"\n🎲 Randomization Options:")
        print("   1. Random draw (different results each time)")
        print("   2. Reproducible draw (same results with same entries)")
        
        try:
            choice = input("Choose option (1 or 2, default: 1): ").strip()
        except KeyboardInterrupt:
            print("\n\n⚠️ Draw cancelled by user")
            return
        
        if choice == "2":
            # Use a seed for reproducible results
            seed = "reproducible-draw"
            print("🔒 Using reproducible mode (same results each time)")
        else:
            # No seed for truly random results
            seed = None
            print("🎲 Using random mode (different results each time)")

    # Create lottery draw
    draw = LotteryDraw(entries=entries, winners_to_pick=winners_to_pick, seed=seed)

    input("\nPress Enter to shuffle the entries...")
    shuffled = draw.shuffle()
    print("✅ Entries have been shuffled!")
    print("🔀 Draw order has been randomized")

    print("\n🏆 Now drawing winners one by one...")
    print("   Press Enter to reveal each winner")

    winners = []
    for i in range(winners_to_pick):
        try:
            input(f"\nPress Enter to draw winner #{i+1}...")
        except KeyboardInterrupt:
            print("\n\n⚠️  Draw interrupted by user")
            return
        
        winner = draw.pick_next()
        winners.append(winner)
        
        print(f"🎉 Winner #{winner.rank}: {winner.registration_no}")
        print(f"   Drawn at: {winner.picked_at.strftime('%H:%M:%S')}")
        
        # Show progress
        remaining_count = winners_to_pick - len(winners)
        if remaining_count > 0:
            print(f"   ({remaining_count} winners remaining)")

    # Show final results
    print("\n" + "="*50)
    print(f"🏆 FINAL RESULTS - ALL {winners_to_pick} WINNERS:")
    print("="*50)
    for winner in winners:
        print(f"Rank {winner.rank:2d}: {winner.registration_no}")

    # Show summary statistics
    state = draw.state()
    print(f"\n📊 Draw Summary:")
    print(f"   Total entries: {state.total}")
    print(f"   Winners selected: {state.picked_count}")
    print(f"   Entries remaining: {len(state.remaining)}")
    print(f"   Status: {state.status}")
    print(f"   Input hash: {state.input_hash[:16]}... (for audit)")

    # Ask if user wants to see more details
    try:
        show_more = input("\nWould you like to see the remaining entries? (y/N): ")
        if show_more.lower().startswith('y'):
            print(f"\n📋 Remaining {len(state.remaining)} entries:")
            for i, reg_no in enumerate(state.remaining, 1):
                print(f"  {i:2d}. {reg_no}")
                if i % 10 == 0 and i < len(state.remaining):
                    input(f"    Press Enter to see next 10 entries...")
    except KeyboardInterrupt:
        print()

    # Ask if user wants to export CSV
    try:
        export_csv = input("\nWould you like to export results to CSV? (y/N): ")
        if export_csv.lower().startswith('y'):
            csv_output = draw.export_csv()
            with open("lottery_results.csv", "w", encoding="utf-8") as f:
                f.write(csv_output)
            print("✅ Results exported to 'lottery_results.csv'")
            print("   CSV contains all entries with winner status and rankings")
    except KeyboardInterrupt:
        print()

    print(f"\n🎊 Interactive lottery draw completed!")
    print("   Thank you for using the lottery_engine!")


if __name__ == "__main__":
    main()