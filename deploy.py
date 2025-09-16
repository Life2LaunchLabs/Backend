#!/usr/bin/env python
"""
Deployment script for Railway that resets database and starts the application.
This script is run during Railway deployment to ensure fresh database state.
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    print(f"Command: {command}")

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running {description}:")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False
    else:
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True

def main():
    """Main deployment process"""
    print("🚀 Starting deployment process...")

    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

    # Check if this is a database reset deployment (set via Railway environment variable)
    reset_db = os.environ.get('RESET_DATABASE_ON_DEPLOY', 'false').lower() == 'true'

    if reset_db:
        print("🗄️  Database reset requested...")

        # Run database reset
        if not run_command(
            "python manage.py reset_database --no-input --confirm",
            "Database reset and migration"
        ):
            print("❌ Database reset failed")
            sys.exit(1)
    else:
        print("📦 Running standard migrations...")

        # Run standard migrations
        if not run_command(
            "python manage.py migrate",
            "Database migrations"
        ):
            print("❌ Migrations failed")
            sys.exit(1)

        # Create default user if it doesn't exist
        if not run_command(
            "python manage.py createdefaultuser",
            "Creating default user"
        ):
            print("⚠️  Default user creation failed (may already exist)")

    # Collect static files
    if not run_command(
        "python manage.py collectstatic --noinput",
        "Collecting static files"
    ):
        print("⚠️  Static file collection failed")
        # Don't exit on static file failure as it's not critical

    print("✅ Deployment process completed successfully!")

if __name__ == "__main__":
    main()