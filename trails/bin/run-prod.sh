#!/bin/bash
python manage.py migrate
gunicorn trails.wsgi --bind 0.0.0.0:$PORT
