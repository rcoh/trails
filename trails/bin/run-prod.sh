#!/bin/bash
gunicorn trails.wsgi --bind 0.0.0.0:$PORT
