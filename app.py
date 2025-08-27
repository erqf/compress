import os
import subprocess
import re
from flask import Flask, request, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO
import math

print("--- app.py se pokreće (V9 Obsidian) ---")

app = Flask(__name__)
app.config['SECRET_key'] = 'finalna-tajna-za-localhost'
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
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=10)
        return float(result.stdout)
    except Exception as e:
        print(f"ERROR: Could not get video duration for {filepath}: {e}")
        return None

def compress_video_task(sid, original_path, filename, target_size_mb):
    try:
        socketio.emit('status_message', {'message': 'Analiziram video...'}, to=sid)
        duration = get_video_duration(original_path)
        if not duration:
            socketio.emit('job_error', {'error': 'Nije moguće pročitati trajanje videa.'}, to=sid)
            return

        target_total_bitrate = (target_size_mb * 1024 * 1024 * 8) / duration
        audio_bitrate = 128 * 1000
        video_bitrate = target_total_bitrate - audio_bitrate

        if video_bitrate <= 0:
            socketio.emit('job_error', {'error': f'Ciljana veličina ({target_size_mb}MB) je preniska za ovaj video.'}, to=sid)
            return

        compressed_filename = f"kompresovan_{target_size_mb}mb_{filename}"
        compressed_path = os.path.join(COMPRESSED_FOLDER, compressed_filename)
        
        socketio.emit('status_message', {'message': 'Pripremam enkodiranje (Pass 1/2)...'}, to=sid)
        cmd_pass1 = ['ffmpeg', '-y', '-i', original_path, '-c:v', 'libx264', '-b:v', f'{int(video_bitrate)}', '-pass', '1', '-an', '-f', 'mp4', os.devnull]
        subprocess.run(cmd_pass1, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        socketio.emit('status_message', {'message': 'Finaliziram kompresiju (Pass 2/2)...'}, to=sid)
        cmd_pass2 = [
            'ffmpeg', '-y', '-i', original_path, '-c:v', 'libx264', '-b:v', f'{int(video_bitrate)}',
            '-pass', '2', '-c:a', 'aac', '-b:a', '128k', '-progress', 'pipe:1', compressed_path
        ]
        process = subprocess.Popen(cmd_pass2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8')
        
        for line in process.stdout:
            match = re.search(r"out_time_ms=(\d+)", line)
            if match:
                elapsed_ms = int(match.group(1))
                progress = 50 + ((elapsed_ms / (duration * 1000000)) * 50)
                socketio.emit('progress_update', {'progress': min(progress, 100)}, to=sid)
        
        process.wait()

        if process.returncode == 0:
            original_size = os.path.getsize(original_path)
            compressed_size = os.path.getsize(compressed_path)
            socketio.emit('job_complete', {
                'download_url': f'/download/{compressed_filename}',
                'original_size': original_size, 'compressed_size': compressed_size
            }, to=sid)
        else:
            socketio.emit('job_error', {'error': 'Došlo je do greške tokom enkodiranja.'}, to=sid)
    except Exception as e:
        socketio.emit('job_error', {'error': f'Došlo je do interne greške na serveru: {str(e)}'}, to=sid)
    finally:
        if os.path.exists(original_path): os.remove(original_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files.get('file')
        target_size_mb = request.form.get('target_size', 8, type=int)
        # ISPRAVKA: Čitamo 'sid' koji nam šalje JavaScript
        sid = request.form.get('sid')

        if not file or not sid:
            return jsonify({'error': 'Fajl ili SID nedostaje.'}), 400

        filename = file.filename
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_path)
        
        # ISPRAVKA: Prosleđujemo ispravan 'sid'
        socketio.start_background_task(compress_video_task, sid, original_path, filename, target_size_mb)
        return jsonify({'success': 'Upload primljen, kompresija počinje.'})
    except Exception as e:
        print(f"ERROR: Greška unutar /upload rute: {e}")
        return jsonify({'error': f'Greška pri uploadu fajla: {str(e)}'}), 500

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(COMPRESSED_FOLDER, filename, as_attachment=True)

@socketio.on('connect')
def handle_connect():
    print(f"Klijent povezan: {request.sid}")

if __name__ == '__main__':
    print("--- Pokrećem server ---")
    socketio.run(app, debug=True, port=5001)