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

        # Step 2: Drop all tables (handles PostgreSQL/other DBs differently)
        self.stdout.write('Dropping all database tables...')
        self.drop_all_tables()

        # Step 3: Create fresh migrations
        self.stdout.write('Creating fresh migrations...')
        call_command('makemigrations')

        # Step 4: Apply migrations
        self.stdout.write('Applying migrations...')
        call_command('migrate')

        # Step 5: Create starter content
        self.stdout.write('Creating starter content...')
        self.create_starter_content()

        self.stdout.write(
            self.style.SUCCESS(
                'Database reset complete! Fresh database with starter content created.'
            )
        )

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

    def create_starter_content(self):
        """Create initial content for the application"""
        # Create default admin user
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(f'  Created admin user: admin/admin123')

        # Create sample courses if Course model exists
        try:
            from apps.courses.models import Course, UserCourseProgress

            # Create root course
            if not Course.objects.filter(id='intro').exists():
                intro_course = Course.objects.create(
                    id='intro',
                    title='Introduction to Programming',
                    description='Learn the basics of programming concepts.',
                    x_position=100,
                    y_position=100,
                    order=1,
                    agenda="""# Introduction to Programming

Welcome to your programming journey! In this course, you'll learn:

- Basic programming concepts
- Variables and data types
- Control structures
- Functions and procedures

Let's get started!"""
                )
                self.stdout.write('  Created intro course')

                # Create child courses
                Course.objects.create(
                    id='variables',
                    title='Variables and Data Types',
                    description='Understanding variables and different data types.',
                    parent=intro_course,
                    x_position=200,
                    y_position=150,
                    order=2
                )

                Course.objects.create(
                    id='functions',
                    title='Functions',
                    description='Learn to create and use functions.',
                    parent=intro_course,
                    x_position=300,
                    y_position=200,
                    order=3
                )

                self.stdout.write('  Created sample courses')

        except ImportError:
            self.stdout.write('  Skipped course creation (app not found)')

        # Create sample quests if Quest model exists
        try:
            from apps.quests.models import Quest, Milestone
            from datetime import date, timedelta

            admin_user = User.objects.first()
            if admin_user and not Quest.objects.filter(title='First Steps').exists():
                quest = Quest.objects.create(
                    title='First Steps',
                    description='Complete your first programming tasks',
                    color='#FF6B6B',
                    user=admin_user,
                    created_by=admin_user  # This makes it personal since user == created_by
                )

                Milestone.objects.create(
                    quest=quest,
                    title='Set up development environment',
                    description='Install and configure your coding tools',
                    order=1,
                    finish_date=date.today() + timedelta(days=7)
                )

                Milestone.objects.create(
                    quest=quest,
                    title='Write your first program',
                    description='Create a simple "Hello World" program',
                    order=2,
                    finish_date=date.today() + timedelta(days=14)
                )

                self.stdout.write('  Created sample quest')

        except ImportError:
            self.stdout.write('  Skipped quest creation (app not found)')

        self.stdout.write('  Starter content creation complete')