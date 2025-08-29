import os
from flask import Flask, request, render_template, jsonify
import cloudinary
import cloudinary.uploader
import cloudinary.utils

print("--- app.py se pokreće (V11.2 Precision Fix) ---")

app = Flask(__name__)
# OBAVEZNO UNESI SVOJE ISPRAVNE PODATKE SA CLOUDINARY DASHBOARD-A OVDE!
cloudinary.config( 
  cloud_name = "drlgdcfvn", 
  api_key = "972236491864889", 
  api_secret = "9pJnt6iw8f8BxfXi4WMWajAW-Pc" 
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify(error="Fajl nije poslat."), 400
    
    file_to_upload = request.files['file']
    target_size_mb = request.form.get('target_size', 8, type=int)
    
    try:
        print(f"Pokušavam da uploadujem '{file_to_upload.filename}' na Cloudinary...")
        upload_result = cloudinary.uploader.upload(
            file_to_upload,
            resource_type = "video"
        )
        
        public_id = upload_result.get('public_id')
        duration = upload_result.get('duration')

        if not duration:
            return jsonify(error="Cloudinary nije uspeo da pročita trajanje videa."), 500
            
        print(f"Upload uspešan. Public ID: {public_id}, Trajanje: {duration}s")
        
        MIN_VIDEO_BITRATE = 100 * 1000
        target_total_bitrate = (target_size_mb * 1024 * 1024 * 8) / duration
        audio_bitrate = 128 * 1000
        video_bitrate = target_total_bitrate - audio_bitrate

        if video_bitrate < MIN_VIDEO_BITRATE:
            error_msg = f'Ciljana veličina ({target_size_mb}MB) je preniska za trajanje ovog videa. Probajte veću vrednost.'
            return jsonify(error=error_msg), 400

        # ISPRAVKA: Dodajemo ":constant" da nateramo Cloudinary da poštuje tačan bitrate
        video_bitrate_str = f"{round(video_bitrate / 1000)}k:constant"
        print(f"Izračunati video bitrate (CBR): {video_bitrate_str}")

        compressed_url = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="video",
            transformation=[
                {'bit_rate': video_bitrate_str},
                {'audio_codec': 'aac'}
            ],
            flags="attachment"
        )[0]
        
        print(f"Kompresovani URL: {compressed_url}")
        
        return jsonify(download_url=compressed_url)

    except Exception as e:
        print(f"Cloudinary greška: {e}")
        return jsonify(error=f"Došlo je do greške sa Cloudinary servisom: {str(e)}"), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, port=port, host='0.0.0.0')
