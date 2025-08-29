#!/bin/bash
# ISPRAVKA: Pokrećemo 'app:app' umesto 'app:socketio'
python -m gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT} app:app
