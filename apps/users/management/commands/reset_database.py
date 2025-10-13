import os
import shutil
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Wipes database, removes migrations, creates fresh migrations and applies them with starter content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to wipe the database',
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Run without interactive prompts (for deployment)',
        )

    def handle(self, *args, **options):
        if not options['confirm'] and not options['no_input']:
            confirmation = input(
                "This will completely wipe your database and all data. "
                "Are you sure you want to continue? (yes/no): "
            )
            if confirmation.lower() != 'yes':
                self.stdout.write(
                    self.style.SUCCESS('Operation cancelled.')
                )
                return

        self.stdout.write(
            self.style.WARNING('Starting database reset process...')
        )

        # Step 1: Remove all migration files except __init__.py
        self.stdout.write('Removing migration files...')
        self.remove_migration_files()

        # Step 2: Clean up media files
        self.stdout.write('Cleaning up media files...')
        self.cleanup_media_files()

        # Step 3: Drop all tables (handles PostgreSQL/other DBs differently)
        self.stdout.write('Dropping all database tables...')
        self.drop_all_tables()

        # Step 4: Create fresh migrations
        self.stdout.write('Creating fresh migrations...')
        call_command('makemigrations')

        # Step 5: Apply migrations
        self.stdout.write('Applying migrations...')
        call_command('migrate')

        self.stdout.write(
            self.style.SUCCESS(
                'Database reset complete! Fresh database schema created.'
            )
        )

    def cleanup_media_files(self):
        """Clean up all media files"""
        # Clean up activities media
        activities_media_dir = os.path.join(settings.MEDIA_ROOT, 'activities')
        if os.path.exists(activities_media_dir):
            try:
                shutil.rmtree(activities_media_dir)
                self.stdout.write(f'  Removed {activities_media_dir}')
            except Exception as e:
                self.stdout.write(f'  Warning: Could not remove activities media: {e}')

        # Clean up profile photos
        profile_photos_dir = os.path.join(settings.MEDIA_ROOT, 'profile_photos')
        if os.path.exists(profile_photos_dir):
            try:
                shutil.rmtree(profile_photos_dir)
                self.stdout.write(f'  Removed {profile_photos_dir}')
            except Exception as e:
                self.stdout.write(f'  Warning: Could not remove profile photos: {e}')

        # Also clean up old activity_media directory if it exists
        old_media_dir = os.path.join(settings.MEDIA_ROOT, 'activity_media')
        if os.path.exists(old_media_dir):
            try:
                shutil.rmtree(old_media_dir)
                self.stdout.write(f'  Removed old {old_media_dir}')
            except Exception as e:
                self.stdout.write(f'  Warning: Could not remove old activity_media: {e}')

    def remove_migration_files(self):
        """Remove all migration files except __init__.py"""
        apps_dir = os.path.join(settings.BASE_DIR, 'apps')

        for app_name in os.listdir(apps_dir):
            app_path = os.path.join(apps_dir, app_name)
            if os.path.isdir(app_path):
                migrations_dir = os.path.join(app_path, 'migrations')
                if os.path.exists(migrations_dir):
                    for file in os.listdir(migrations_dir):
                        if file.endswith('.py') and file != '__init__.py':
                            file_path = os.path.join(migrations_dir, file)
                            os.remove(file_path)
                            self.stdout.write(f'  Removed {file_path}')

    def drop_all_tables(self):
        """Drop all tables from the database"""
        with connection.cursor() as cursor:
            # Get database engine
            engine = connection.settings_dict['ENGINE']

            if 'postgresql' in engine:
                # PostgreSQL specific
                cursor.execute("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                """)
            elif 'sqlite' in engine:
                # SQLite specific
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                for table in tables:
                    if table[0] != 'sqlite_sequence':
                        cursor.execute(f'DROP TABLE IF EXISTS {table[0]};')
            else:
                # Generic approach - get all tables and drop them
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                """)
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f'DROP TABLE IF EXISTS {table[0]} CASCADE;')

