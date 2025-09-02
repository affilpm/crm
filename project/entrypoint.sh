#!/bin/sh

# Wait for DB to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "PostgreSQL started!"

# Apply migrations
python manage.py migrate --noinput

# Collect static files (optional, for production)
python manage.py collectstatic --noinput

# Start server with Gunicorn on port 80
gunicorn project.wsgi:application --bind 0.0.0.0:80