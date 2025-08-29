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

# NOVO: Dajemo dozvolu da se naša start.sh skripta izvrši
RUN chmod +x /app/start.sh

# NOVO: Finalna komanda sada samo pokreće našu skriptu
CMD ["/app/start.sh"]
