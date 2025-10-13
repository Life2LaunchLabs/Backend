from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationAdmin

User = get_user_model()

class Command(BaseCommand):
    help = 'Create default admin user if it does not exist'

    def handle(self, *args, **options):
        # Create or get the user
        user_created = False
        try:
            user = User.objects.get(email='sam@fake.com')
            self.stdout.write(f'User {user.email} already exists')
        except User.DoesNotExist:
            user = User.objects.create_superuser(
                email='sam@fake.com',
                password='samgarcia',
                first_name='Sam',
                last_name='Garcia'
            )
            # Add profile defaults
            user.bio = "I'm redefining human centered design in a high tech era. Open to work helping your business with branding, marketing, and social media."
            user.tagline = "Visionary designer and recent high school graduate"
            user.save()
            user_created = True
            self.stdout.write(f'Created user: {user.email}')

        # Always set up organizations (regardless of whether user existed)
        organizations_data = [
            {'name': 'Life2Launch', 'slug': 'life2launch', 'description': 'Life2Launch organization'},
            {'name': 'Test Organization', 'slug': 'test', 'description': 'Test organization for development'}
        ]

        organizations = []
        for org_data in organizations_data:
            try:
                org = Organization.objects.get(slug=org_data['slug'])
                self.stdout.write(f'Organization {org_data["name"]} already exists')
            except Organization.DoesNotExist:
                org = Organization.objects.create(**org_data)
                self.stdout.write(f'Created organization: {org_data["name"]}')

            organizations.append(org)

        # Make Sam an admin of both organizations
        for org in organizations:
            admin_relation, created = OrganizationAdmin.objects.get_or_create(
                user=user,
                organization=org,
                defaults={'role': 'admin'}
            )
            if created:
                self.stdout.write(f'Made {user.email} admin of {org.name}')
            else:
                self.stdout.write(f'{user.email} is already admin of {org.name}')

        # Set default organization to Life2Launch (first one)
        if organizations:
            user.default_organization = organizations[0]  # Life2Launch
            user.save(update_fields=['default_organization'])
            self.stdout.write(f'Set default organization to {organizations[0].name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up admin user {user.email} with organizations: '
                f'{", ".join([org.name for org in organizations])}'
            )
        )

        # Create demo activities and quest
        try:
            from django.core.management import call_command

            # Create demo activities
            self.stdout.write('Creating demo activities...')
            call_command('create_demo_from_json')

            # Create demo quest
            self.stdout.write('Creating demo quest...')
            call_command('create_demo_quest')

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Failed to create demo data: {e}')
            )

        final_message = 'Successfully created demo user: sam@fake.com/samgarcia' if user_created else 'Successfully updated existing user with admin organizations'
        self.stdout.write(
            self.style.SUCCESS(final_message)
        )