# Koristimo zvaničnu, laganu verziju Pythona kao osnovu
FROM python:3.9-slim

# Kažemo sistemu da ažurira svoje pakete i INSTALIRA FFmpeg
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Postavljamo radni direktorijum unutar servera
WORKDIR /app

# Kopiramo listu potrebnih biblioteka i instaliramo ih
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Kopiramo ostatak naše aplikacije
COPY . .

# Finalna komanda koja pokreće naš server
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:${PORT}", "app:socketio"]
