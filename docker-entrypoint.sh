#!/bin/bash
set -e

# Wait for database to be ready (if you have a wait-for-it script)
# ./wait-for-it.sh $DB_HOST:$DB_PORT

# Create database schema if it doesn't exist
python -c "
from src.configs.database import init_db
import asyncio
asyncio.run(init_db())
"

# Run migrations
alembic upgrade head

# Start the application
exec python -m src.main
