# app.py (V9.2 - Optimizovan za Free Tier)
import os
import subprocess
import re
from flask import Flask, request, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO
import math

print("--- app.py se pokreće (V9.2 Optimizovan) ---")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'finalna-tajna-za-localhost'
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024
socketio = SocketIO(app)

UPLOAD_FOLDER = 'uploads'
COMPRESSED_FOLDER = 'compressed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_video_duration(filepath):
    try:
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=15)
        return float(result.stdout)
    except Exception as e:
        print(f"ERROR: Could not get video duration for {filepath}: {e}")
        return None

def compress_video_task(sid, original_path, filename, target_size_mb):
    try:
        socketio.emit('status_message', {'message': 'Analiziram video...'}, to=sid)
        duration = get_video_duration(original_path)
        if not duration:
            socketio.emit('job_error', {'error': 'Nije moguće pročitati trajanje videa. Fajl je možda oštećen.'}, to=sid)
            return

        MIN_VIDEO_BITRATE = 100 * 1000 
        target_total_bitrate = (target_size_mb * 1024 * 1024 * 8) / duration
        audio_bitrate = 128 * 1000
        video_bitrate = target_total_bitrate - audio_bitrate

        if video_bitrate < MIN_VIDEO_BITRATE:
            error_msg = f'Ciljana veličina ({target_size_mb}MB) je preniska za trajanje ovog videa. Probajte veću vrednost.'
            socketio.emit('job_error', {'error': error_msg}, to=sid)
            return

        compressed_filename = f"kompresovan_{target_size_mb}mb_{filename}"
        compressed_path = os.path.join(COMPRESSED_FOLDER, compressed_filename)
        
        max_rate = int(video_bitrate * 1.2)
        buf_size = int(video_bitrate * 2)

        socketio.emit('status_message', {'message': 'Započinjem kompresiju (1-Pass VBR)...'}, to=sid)
        
        # OPTIMIZACIJA: Jedan prolaz (1-Pass) umesto dva. Mnogo brže i pouzdanije na slabim serverima.
        cmd = [
            'ffmpeg', '-y', '-i', original_path,
            '-c:v', 'libx264', '-b:v', f'{int(video_bitrate)}',
            '-maxrate', f'{max_rate}', '-bufsize', f'{buf_size}',
            '-c:a', 'aac', '-b:a', '128k',
            '-progress', 'pipe:1',
            compressed_path
        ]
        
        # Povećavamo timeout jer kompresija može da traje. Npr. 10 minuta (600 sekundi).
        process_timeout = 600 

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8')
        
        for line in process.stdout:
            match = re.search(r"out_time_ms=(\d+)", line)
            if match:
                elapsed_ms = int(match.group(1))
                progress = (elapsed_ms / (duration * 1000000)) * 100
                socketio.emit('progress_update', {'progress': min(progress, 100)}, to=sid)
                socketio.emit('status_message', {'message': f'Kompresija u toku: {min(progress, 100):.1f}%'}, to=sid)
        
        # Čekamo da se proces završi, ali sa timeout-om
        process.wait(timeout=process_timeout)

        if process.returncode == 0:
            original_size = os.path.getsize(original_path)
            compressed_size = os.path.getsize(compressed_path)
            socketio.emit('job_complete', {
                'download_url': f'/download/{compressed_filename}',
                'original_size': original_size, 'compressed_size': compressed_size
            }, to=sid)
        else:
            socketio.emit('job_error', {'error': 'Došlo je do greške tokom enkodiranja.'}, to=sid)
            
    except subprocess.TimeoutExpired:
        socketio.emit('job_error', {'error': f'Proces je trajao predugo (preko {process_timeout/60} min) i prekinut je. Probajte sa manjim fajlom.'}, to=sid)
    except Exception as e:
        socketio.emit('job_error', {'error': f'Došlo je do interne greške na serveru: {str(e)}'}, to=sid)
    finally:
        if os.path.exists(original_path): os.remove(original_path)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')
        target_size_mb = request.form.get('target_size', 8, type=int)
        sid = request.form.get('sid')
        if not file or not sid: return jsonify({'error': 'Fajl ili SID nedostaje.'}), 400
        filename = file.filename
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_path)
        socketio.start_background_task(compress_video_task, sid, original_path, filename, target_size_mb)
        return jsonify({'success': 'Upload primljen, kompresija počinje.'})
    except Exception as e: return jsonify({'error': f'Greška pri uploadu fajla: {str(e)}'}), 500

@app.route('/download/<filename>')
def download(filename): return send_from_directory(COMPRESSED_FOLDER, filename, as_attachment=True)

@socketio.on('connect')
def handle_connect(): print(f"Klijent povezan: {request.sid}")

if __name__ == '__main__':
    print("--- Pokrećem server ---")
    socketio.run(app, debug=True, port=5001)
