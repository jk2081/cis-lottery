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

# Add parent directory to path for both local and production environments
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from lottery_engine import Entry, LotteryDraw, LotteryError

app = Flask(__name__)
app.secret_key = 'lottery-gui-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Global simple state - much simpler than sessions
lottery_state = {
    'entries': [],
    'winners_to_pick': 0,
    'draw': None,
    'is_shuffled': False,
    'winners': [],
    'input_source': '',
    'randomization_mode': 'random'
}

def reset_lottery_state():
    """Reset the global lottery state."""
    global lottery_state
    lottery_state = {
        'entries': [],
        'winners_to_pick': 0,
        'draw': None,
        'is_shuffled': False,
        'winners': [],
        'input_source': '',
        'randomization_mode': 'random'
    }


def get_lottery_state():
    """Get current lottery state as a simple dict."""
    return {
        'entry_count': len(lottery_state['entries']),
        'winners_to_pick': lottery_state['winners_to_pick'],
        'is_shuffled': lottery_state['is_shuffled'],
        'winner_count': len(lottery_state['winners']),
        'winners': [
            {
                'registration_no': w.registration_no,
                'rank': w.rank,
                'picked_at': w.picked_at.isoformat()
            } for w in lottery_state['winners']
        ],
        'input_source': lottery_state['input_source'],
        'randomization_mode': lottery_state['randomization_mode'],
        'is_completed': lottery_state['draw'] and lottery_state['draw'].state().status == "Completed",
        'entries_list': [entry.registration_no for entry in lottery_state['entries']] if lottery_state['entries'] else None
    }


@app.route('/')
def index():
    """Serve the main lottery interface."""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current lottery status."""
    return jsonify(get_lottery_state())


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
        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError as e:
            return jsonify({'error': 'File must be UTF-8 encoded'}), 400
        
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
        
        # Update global state - much simpler!
        lottery_state['entries'] = entries
        lottery_state['winners_to_pick'] = winners_to_pick
        lottery_state['input_source'] = f"CSV file: {file.filename}"
        lottery_state['is_shuffled'] = False
        lottery_state['draw'] = None
        lottery_state['winners'] = []
        
        return jsonify({
            'success': True,
            'entry_count': len(entries),
            'winners_to_pick': winners_to_pick,
            'sample_entries': [e.registration_no for e in entries[:5]],
            'entries_list': [e.registration_no for e in entries],
            'source': lottery_state['input_source']
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
        
        # Update global state
        lottery_state['entries'] = entries
        lottery_state['winners_to_pick'] = winners_to_pick
        lottery_state['input_source'] = "Manual input"
        lottery_state['is_shuffled'] = False
        lottery_state['draw'] = None
        lottery_state['winners'] = []
        
        return jsonify({
            'success': True,
            'entry_count': len(entries),
            'winners_to_pick': winners_to_pick,
            'sample_entries': [e.registration_no for e in entries[:5]],
            'entries_list': [e.registration_no for e in entries],
            'source': lottery_state['input_source']
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing entries: {str(e)}'}), 500


@app.route('/api/shuffle', methods=['POST'])
def shuffle_lottery():
    """Create and shuffle the lottery draw."""
    try:
        if not lottery_state['entries']:
            return jsonify({'error': 'No entries loaded'}), 400
        
        data = request.get_json() or {}
        randomization_mode = data.get('mode', 'random')
        
        # Determine seed based on mode
        seed = None if randomization_mode == 'random' else 'reproducible-draw'
        
        # Create lottery draw
        lottery_state['draw'] = LotteryDraw(
            entries=lottery_state['entries'],
            winners_to_pick=lottery_state['winners_to_pick'],
            seed=seed
        )
        
        # Shuffle
        lottery_state['draw'].shuffle()
        lottery_state['is_shuffled'] = True
        lottery_state['randomization_mode'] = randomization_mode
        lottery_state['winners'] = []
        
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
        if not lottery_state['draw'] or not lottery_state['is_shuffled']:
            return jsonify({'error': 'Lottery not shuffled'}), 400
        
        if lottery_state['draw'].state().status == "Completed":
            return jsonify({'error': 'All winners already drawn'}), 400
        
        # Pick next winner
        winner = lottery_state['draw'].pick_next()
        lottery_state['winners'].append(winner)
        
        state = lottery_state['draw'].state()
        
        return jsonify({
            'success': True,
            'winner': {
                'registration_no': winner.registration_no,
                'rank': winner.rank,
                'picked_at': winner.picked_at.isoformat()
            },
            'is_completed': state.status == "Completed",
            'remaining_count': len(state.remaining),
            'total_drawn': len(lottery_state['winners'])
        })
        
    except LotteryError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error drawing winner: {str(e)}'}), 500


@app.route('/api/export')
def export_results():
    """Export lottery results as CSV."""
    try:
        if not lottery_state['draw']:
            return jsonify({'error': 'No lottery to export'}), 400
        
        # Generate CSV export
        csv_content = lottery_state['draw'].export_csv()
        
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
    """Reset the lottery state."""
    reset_lottery_state()
    return jsonify({'success': True, 'message': 'Lottery reset'})


if __name__ == '__main__':
    import sys
    
    # Get port from environment (for Railway/Heroku) or command line argument
    port = int(os.environ.get('PORT', 8080))
    
    # Allow custom port via command line argument (for local development)
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Usage: python app.py [port_number]")
            print(f"Using port {port}")
    
    # Determine if we're running in production
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER') or os.environ.get('HEROKU_APP_NAME')
    
    if is_production:
        print("🎲 Starting Lottery GUI Web Application (Production)")
        print(f"🌐 Running on port {port}")
        app.run(debug=False, host='0.0.0.0', port=port)
    else:
        print("🎲 Starting Lottery GUI Web Application (Development)")
        print(f"📍 Open your browser to: http://localhost:{port}")
        print("🛑 Press Ctrl+C to stop the server")
        print(f"💡 If port {port} is busy, try: python app.py 3000")
        
        try:
            app.run(debug=True, host='localhost', port=port)
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"\n❌ Port {port} is already in use!")
                print("💡 Try a different port: python app.py 3000")
                print("🍎 On macOS, disable AirPlay Receiver in System Preferences")
            else:
                raise