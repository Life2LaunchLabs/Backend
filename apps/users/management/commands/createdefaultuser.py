from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create default admin user if it does not exist'

    def handle(self, *args, **options):
        if not User.objects.filter(email='sam@fake.com').exists():
            user = User.objects.create_superuser(
                email='sam@fake.com',
                password='samgarcia',
                first_name='Sam',
                last_name='Garcia'
            )
            # Add profile defaults
            user.bio = "Software engineer and tech enthusiast passionate about building great user experiences. Love working with modern web technologies and solving complex problems."
            user.tagline = "Building the future, one line of code at a time"
            user.save()

            # Initialize default quests for the demo user
            try:
                from apps.quests.default_quests_v2 import initialize_default_quests_for_user_v2
                result = initialize_default_quests_for_user_v2(user)
                if result:
                    enrollment_count = len([k for k in result.keys() if 'enrollment' in k])
                    self.stdout.write(
                        self.style.SUCCESS(f'Initialized {enrollment_count} default quest enrollments')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Failed to initialize quests: {e}')
                )

            self.stdout.write(
                self.style.SUCCESS('Successfully created demo user: sam@fake.com/samgarcia')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Demo user already exists')
            )