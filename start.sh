#!/bin/bash
python -m gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT} app:socketio
