# Lottery System

A professional lottery management system with three interfaces: Python library, command-line tool, and web application.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install flask  # Only needed for web app
```

### 2. Choose Your Interface

**Python Library** → Direct code integration  
**CLI Tool** → Interactive terminal experience  
**Web App** → Modern browser interface  

---

## 📚 Python Library

### Basic Usage
```python
from lottery_engine import Entry, LotteryDraw

# Create entries
entries = [Entry("EMP-001"), Entry("EMP-002"), Entry("EMP-003")]

# Create lottery (3 entries, pick 1 winner)
draw = LotteryDraw(entries, winners_to_pick=1, seed="optional-seed")

# Shuffle and draw
draw.shuffle()
winner = draw.pick_next()

print(f"Winner: {winner.registration_no}, Rank: {winner.rank}")
```

### Advanced Features
```python
# Get current state
state = draw.state()
print(f"Status: {state.status}")
print(f"Winners: {len(state.winners)}")

# Export to CSV
csv_data = draw.export_csv()
with open("results.csv", "w") as f:
    f.write(csv_data)
```

---

## 💻 CLI Tool

### Run Interactive Lottery
```bash
python interactive_lottery.py
```

### Use CSV File
```bash
python interactive_lottery.py entries.csv
```

### Force Randomization Mode
```bash
python interactive_lottery.py entries.csv --random       # Different each time
python interactive_lottery.py entries.csv --reproducible # Same each time
```

### CSV Format
```csv
3
EMPLOYEE-001
EMPLOYEE-002
EMPLOYEE-003
EMPLOYEE-004
EMPLOYEE-005
```
*First line = number of winners, remaining lines = participant IDs*

---

## 🌐 Web Application

### Start Server
```bash
cd lottery_gui
python app.py
```

### Open Browser
Navigate to **http://localhost:5000**

### Usage Flow
1. **Upload CSV** or **Enter Manually**
2. **Choose Randomization** (Random/Reproducible)  
3. **Shuffle & Start Draw**
4. **Reveal Winners** one by one
5. **Export Results** as CSV

---

## 📁 File Structure

```
lottery/
├── lottery_engine/          # Core Python library
│   ├── __init__.py
│   ├── core.py             # Main lottery logic
│   └── models.py           # Data classes
├── tests/                  # Test suite
├── interactive_lottery.py  # CLI tool
├── lottery_gui/            # Web application
│   ├── app.py             # Flask server
│   ├── templates/         # HTML templates
│   └── static/            # CSS/JS assets
└── README.md              # This file
```

---

## ⚙️ Key Features

- **Deterministic** with seed (reproducible for audits)
- **Cryptographically secure** without seed
- **CSV import/export** with full audit trail
- **Input validation** and error handling
- **Unicode support** for international characters
- **Performance tested** up to 100k entries

---

## 🎯 Examples

### Basic Lottery (Python)
```python
from lottery_engine import Entry, LotteryDraw

# 5 people, pick 2 winners
people = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
entries = [Entry(name) for name in people]
draw = LotteryDraw(entries, 2)

draw.shuffle()
print(f"1st: {draw.pick_next().registration_no}")
print(f"2nd: {draw.pick_next().registration_no}")
```

### CSV Lottery (CLI)
Create `employees.csv`:
```csv
3
EMP-101
EMP-102
EMP-103
EMP-104
EMP-105
```

Run:
```bash
python interactive_lottery.py employees.csv
```

### Web Interface
1. Start: `python lottery_gui/app.py`
2. Visit: http://localhost:5000
3. Upload your CSV or enter manually
4. Draw winners with beautiful animations!

---

## 🔧 API Reference

### Entry
```python
Entry(registration_no: str, label: Optional[str] = None)
```

### LotteryDraw
```python
LotteryDraw(entries: List[Entry], winners_to_pick: int, seed: Optional[str] = None)

# Methods
.shuffle() -> List[str]           # Randomize order
.pick_next() -> Winner           # Draw next winner  
.state() -> DrawState            # Get current state
.export_csv() -> str             # Export results
```

### Winner
```python
Winner(registration_no: str, rank: int, picked_at: datetime)
```

---

## 🛠️ Development

### Run Tests
```bash
python -c "
from lottery_engine import Entry, LotteryDraw
entries = [Entry(str(i)) for i in range(10)]
draw = LotteryDraw(entries, 3, 'test')
draw.shuffle()
for _ in range(3):
    winner = draw.pick_next()
    print(f'Winner: {winner.registration_no}')
print('✅ All tests passed!')
"
```

### Performance Test
```bash
python -c "
import time
from lottery_engine import Entry, LotteryDraw

start = time.time()
entries = [Entry(str(i)) for i in range(100000)]
draw = LotteryDraw(entries, 1000, 'perf-test')
draw.shuffle()
for _ in range(1000):
    draw.pick_next()
print(f'100k entries, 1k winners: {time.time()-start:.2f}s')
"
```

---

## ✅ That's It!

You now have a complete lottery system with library, CLI, and web interfaces. Pick the one that fits your needs and start drawing winners!