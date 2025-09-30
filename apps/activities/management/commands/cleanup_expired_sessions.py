from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.activities.models import ActivitySession, Attempt


class Command(BaseCommand):
    help = 'Clean up expired activity sessions and old in-progress attempts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']

        # Clean up expired ActivitySessions
        expired_sessions = ActivitySession.objects.filter(expires_at__lt=now)
        session_count = expired_sessions.count()

        if dry_run:
            self.stdout.write(f"Would delete {session_count} expired sessions")
            for session in expired_sessions[:5]:  # Show first 5 as examples
                self.stdout.write(f"  - Session {session.id}: {session.user.username} on {session.activity_version.title}")
        else:
            deleted_count = expired_sessions.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} expired activity sessions')
            )

        # Clean up old in-progress Attempts (legacy - should be migrated to sessions eventually)
        from datetime import timedelta
        cutoff = now - timedelta(hours=24)
        old_attempts = Attempt.objects.filter(
            status__in=['in_progress', 'active'],
            started_at__lt=cutoff
        )
        attempt_count = old_attempts.count()

        if dry_run:
            self.stdout.write(f"Would clean up {attempt_count} old in-progress attempts")
            for attempt in old_attempts[:5]:
                self.stdout.write(f"  - Attempt {attempt.id}: {attempt.user.username if attempt.user else 'No user'}")
        else:
            # Mark as abandoned instead of deleting (preserves audit trail)
            updated_count = old_attempts.update(status='abandoned')
            self.stdout.write(
                self.style.SUCCESS(f'Marked {updated_count} old attempts as abandoned')
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("This was a dry run. Use --dry-run=false to actually clean up."))
        else:
            self.stdout.write(self.style.SUCCESS("Cleanup completed successfully."))