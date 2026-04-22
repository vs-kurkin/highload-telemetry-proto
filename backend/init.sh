#!/bin/bash
set -e

echo "Waiting for database..."
until python -c "import psycopg; psycopg.connect('postgresql://telemetry_user:supersecretpassword@db:5432/telemetry_db')" 2>/dev/null; do
  sleep 1
done

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Creating superuser (if not exists)..."
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin_password')
    print('Superuser created: admin / admin_password')
END

# Check if a command was passed
if [ $# -gt 0 ]; then
  echo "Executing custom command: $@"
  exec "$@"
else
  echo "Starting default server (Daphne)..."
  exec daphne -b 0.0.0.0 -p 8000 telemetry_core.asgi:application
fi
