# Koristimo zvaničnu, laganu verziju Pythona kao osnovu
FROM python:3.9-slim

# Kažemo sistemu da ažurira svoje pakete i INSTALIRA FFmpeg
# Ovo je ključan korak koji nam omogućava da kompresujemo video
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Postavljamo radni direktorijum unutar servera
WORKDIR /app

# Kopiramo listu potrebnih biblioteka i instaliramo ih
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Kopiramo ostatak naše aplikacije (app.py, templates folder, itd.)
COPY . .

# Finalna komanda koja pokreće naš server kada se sve izgradi
# Render automatski daje PORT varijablu
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:${PORT}", "app:socketio"]
