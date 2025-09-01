"""Flask web application for lottery GUI.

A modern, minimalist web interface for the lottery_engine library.
Provides drag-and-drop CSV upload, manual entry, and interactive winner selection.
"""

import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from flask import Flask, render_template, request, jsonify, send_file, session
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lottery_engine import Entry, LotteryDraw, LotteryError

app = Flask(__name__)
app.secret_key = 'lottery-gui-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


class LotterySession:
    """Manages lottery state for a user session."""
    
    def __init__(self):
        self.entries: list[Entry] = []
        self.winners_to_pick: int = 0
        self.draw: Optional[LotteryDraw] = None
        self.is_shuffled: bool = False
        self.winners: list = []
        self.input_source: str = ""
        self.randomization_mode: str = "random"  # or "reproducible"
    
    def reset(self):
        """Reset the session to initial state."""
        self.__init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session state to JSON-serializable dict."""
        return {
            'entry_count': len(self.entries),
            'winners_to_pick': self.winners_to_pick,
            'is_shuffled': self.is_shuffled,
            'winner_count': len(self.winners),
            'winners': [
                {
                    'registration_no': w.registration_no,
                    'rank': w.rank,
                    'picked_at': w.picked_at.isoformat()
                } for w in self.winners
            ],
            'input_source': self.input_source,
            'randomization_mode': self.randomization_mode,
            'is_completed': self.draw and self.draw.state().status == "Completed"
        }


def get_session() -> LotterySession:
    """Get or create lottery session for current user."""
    if 'lottery_session' not in session:
        session['lottery_session'] = LotterySession().to_dict()
    
    # Reconstruct LotterySession object (simplified for this demo)
    lottery_session = LotterySession()
    session_data = session['lottery_session']
    lottery_session.winners_to_pick = session_data.get('winners_to_pick', 0)
    lottery_session.is_shuffled = session_data.get('is_shuffled', False)
    lottery_session.input_source = session_data.get('input_source', "")
    lottery_session.randomization_mode = session_data.get('randomization_mode', "random")
    
    return lottery_session


def save_session(lottery_session: LotterySession):
    """Save lottery session state."""
    session['lottery_session'] = lottery_session.to_dict()


@app.route('/')
def index():
    """Serve the main lottery interface."""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current lottery session status."""
    lottery_session = get_session()
    return jsonify(lottery_session.to_dict())


@app.route('/api/upload', methods=['POST'])
def upload_csv():
    """Handle CSV file upload."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        
        if len(lines) < 2:
            return jsonify({'error': 'CSV must have at least 2 lines (winner count + entries)'}), 400
        
        # Parse winner count
        try:
            winners_to_pick = int(lines[0])
        except ValueError:
            return jsonify({'error': f'First line must be a number, got: {lines[0]}'}), 400
        
        if winners_to_pick <= 0:
            return jsonify({'error': 'Number of winners must be positive'}), 400
        
        # Parse entries
        reg_numbers = lines[1:]
        if len(reg_numbers) == 0:
            return jsonify({'error': 'No registration numbers found'}), 400
        
        if winners_to_pick > len(reg_numbers):
            return jsonify({'error': f'Cannot pick {winners_to_pick} winners from {len(reg_numbers)} entries'}), 400
        
        # Validate unique registration numbers
        seen = set()
        for i, reg_no in enumerate(reg_numbers, 2):
            if not reg_no:
                return jsonify({'error': f'Empty registration number on line {i}'}), 400
            if reg_no in seen:
                return jsonify({'error': f'Duplicate registration number: {reg_no}'}), 400
            seen.add(reg_no)
        
        # Create entries
        entries = [Entry(reg_no) for reg_no in reg_numbers]
        
        # Update session
        lottery_session = get_session()
        lottery_session.reset()
        lottery_session.entries = entries
        lottery_session.winners_to_pick = winners_to_pick
        lottery_session.input_source = f"CSV file: {file.filename}"
        save_session(lottery_session)
        
        return jsonify({
            'success': True,
            'entry_count': len(entries),
            'winners_to_pick': winners_to_pick,
            'sample_entries': [e.registration_no for e in entries[:5]],
            'source': lottery_session.input_source
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/api/manual-entries', methods=['POST'])
def set_manual_entries():
    """Handle manual entry input."""
    try:
        data = request.get_json()
        entries_text = data.get('entries', '').strip()
        winners_to_pick = data.get('winners_to_pick', 0)
        
        if not entries_text:
            return jsonify({'error': 'No entries provided'}), 400
        
        if not isinstance(winners_to_pick, int) or winners_to_pick <= 0:
            return jsonify({'error': 'Winners to pick must be a positive number'}), 400
        
        # Parse entries (one per line)
        reg_numbers = [line.strip() for line in entries_text.split('\n') if line.strip()]
        
        if len(reg_numbers) == 0:
            return jsonify({'error': 'No valid entries found'}), 400
        
        if winners_to_pick > len(reg_numbers):
            return jsonify({'error': f'Cannot pick {winners_to_pick} winners from {len(reg_numbers)} entries'}), 400
        
        # Validate unique entries
        seen = set()
        for reg_no in reg_numbers:
            if reg_no in seen:
                return jsonify({'error': f'Duplicate entry: {reg_no}'}), 400
            seen.add(reg_no)
        
        # Create entries
        entries = [Entry(reg_no) for reg_no in reg_numbers]
        
        # Update session
        lottery_session = get_session()
        lottery_session.reset()
        lottery_session.entries = entries
        lottery_session.winners_to_pick = winners_to_pick
        lottery_session.input_source = "Manual input"
        save_session(lottery_session)
        
        return jsonify({
            'success': True,
            'entry_count': len(entries),
            'winners_to_pick': winners_to_pick,
            'sample_entries': [e.registration_no for e in entries[:5]],
            'source': lottery_session.input_source
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing entries: {str(e)}'}), 500


@app.route('/api/shuffle', methods=['POST'])
def shuffle_lottery():
    """Create and shuffle the lottery draw."""
    try:
        lottery_session = get_session()
        
        if not lottery_session.entries:
            return jsonify({'error': 'No entries loaded'}), 400
        
        data = request.get_json() or {}
        randomization_mode = data.get('mode', 'random')
        
        # Determine seed based on mode
        seed = None if randomization_mode == 'random' else 'reproducible-draw'
        
        # Create lottery draw
        lottery_session.draw = LotteryDraw(
            entries=lottery_session.entries,
            winners_to_pick=lottery_session.winners_to_pick,
            seed=seed
        )
        
        # Shuffle
        lottery_session.draw.shuffle()
        lottery_session.is_shuffled = True
        lottery_session.randomization_mode = randomization_mode
        lottery_session.winners = []
        
        save_session(lottery_session)
        
        return jsonify({
            'success': True,
            'is_shuffled': True,
            'randomization_mode': randomization_mode,
            'ready_to_draw': True
        })
        
    except LotteryError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error shuffling lottery: {str(e)}'}), 500


@app.route('/api/draw-winner', methods=['POST'])
def draw_winner():
    """Draw the next winner."""
    try:
        lottery_session = get_session()
        
        if not lottery_session.draw or not lottery_session.is_shuffled:
            return jsonify({'error': 'Lottery not shuffled'}), 400
        
        if lottery_session.draw.state().status == "Completed":
            return jsonify({'error': 'All winners already drawn'}), 400
        
        # Pick next winner
        winner = lottery_session.draw.pick_next()
        lottery_session.winners.append(winner)
        
        state = lottery_session.draw.state()
        save_session(lottery_session)
        
        return jsonify({
            'success': True,
            'winner': {
                'registration_no': winner.registration_no,
                'rank': winner.rank,
                'picked_at': winner.picked_at.isoformat()
            },
            'is_completed': state.status == "Completed",
            'remaining_count': len(state.remaining),
            'total_drawn': len(lottery_session.winners)
        })
        
    except LotteryError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error drawing winner: {str(e)}'}), 500


@app.route('/api/export')
def export_results():
    """Export lottery results as CSV."""
    try:
        lottery_session = get_session()
        
        if not lottery_session.draw:
            return jsonify({'error': 'No lottery to export'}), 400
        
        # Generate CSV export
        csv_content = lottery_session.draw.export_csv()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False,
            encoding='utf-8'
        )
        temp_file.write(csv_content)
        temp_file.close()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'lottery_results_{timestamp}.csv'
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({'error': f'Error exporting results: {str(e)}'}), 500


@app.route('/api/reset', methods=['POST'])
def reset_lottery():
    """Reset the lottery session."""
    lottery_session = get_session()
    lottery_session.reset()
    save_session(lottery_session)
    
    return jsonify({'success': True, 'message': 'Lottery reset'})


if __name__ == '__main__':
    print("🎲 Starting Lottery GUI Web Application")
    print("📍 Open your browser to: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='localhost', port=5000)