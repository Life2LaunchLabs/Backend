#!/usr/bin/env python
"""
Manual database reset script for local development.
Use this when you want to completely reset your local database.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.core.management import call_command

def main():
    print("🗄️  Resetting database...")
    print("This will completely wipe your local database and recreate it with fresh data.")

    confirmation = input("Are you sure you want to continue? (yes/no): ")
    if confirmation.lower() != 'yes':
        print("Operation cancelled.")
        return

    try:
        call_command('reset_database', '--confirm')
        print("✅ Database reset completed successfully!")
        print("You can now start your development server with: uvicorn mysite.asgi:application --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Error during database reset: {e}")

if __name__ == "__main__":
    main()