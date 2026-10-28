#!/usr/bin/env bash
# Runs on every Render deploy. Every step is safe to repeat.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py createcachetable

# Creates the admin user from environment variables. Does nothing if it exists.
python manage.py createsuperuser --no-input || true

# DEMO data. Replace with real values before a real shop uses the app.
python manage.py seed_catalog
python manage.py load_recommendations
python manage.py seed_pairings