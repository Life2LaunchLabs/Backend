from django.core.management.base import BaseCommand
from django.db import transaction
from apps.activities.models import Attempt, ActivitySubmission, SubmissionResponse


class Command(BaseCommand):
    help = 'Migrate completed attempts to ActivitySubmission records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find completed attempts that haven't been migrated yet
        completed_attempts = Attempt.objects.filter(status='completed')

        self.stdout.write(f"Found {completed_attempts.count()} completed attempts to migrate")

        migrated_count = 0

        for attempt in completed_attempts:
            # Check if submission already exists for this attempt
            existing_submission = ActivitySubmission.objects.filter(
                user=attempt.user,
                activity_version=attempt.activity_version,
                started_at=attempt.started_at
            ).first()

            if existing_submission:
                self.stdout.write(f"  Skipping {attempt.id} - submission already exists")
                continue

            if dry_run:
                responses_count = attempt.responses.count()
                self.stdout.write(
                    f"  Would migrate attempt {attempt.id}: "
                    f"{attempt.user.username if attempt.user else 'No user'} - "
                    f"{attempt.activity_version.title} "
                    f"({responses_count} responses)"
                )
            else:
                try:
                    with transaction.atomic():
                        # Calculate completion time
                        if attempt.completed_at and attempt.started_at:
                            time_taken = attempt.completed_at - attempt.started_at
                        else:
                            # Fallback if completed_at is missing
                            from datetime import timedelta
                            time_taken = timedelta(minutes=30)  # Default

                        # Create submission
                        submission = ActivitySubmission.objects.create(
                            user=attempt.user,
                            activity_version=attempt.activity_version,
                            quest_instance=attempt.quest_instance,
                            started_at=attempt.started_at,
                            time_taken=time_taken,
                            meta=attempt.meta
                        )

                        # Migrate responses
                        for response in attempt.responses.all():
                            SubmissionResponse.objects.create(
                                submission=submission,
                                question_id=response.question_id,
                                question_type=response.question_type,
                                page=response.page,
                                value=response.value,
                                valid=response.valid,
                                meta=response.meta
                            )

                        # Delete the old attempt
                        attempt.delete()
                        migrated_count += 1

                        self.stdout.write(
                            f"  ✓ Migrated attempt {attempt.id} to submission {submission.id}"
                        )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Failed to migrate attempt {attempt.id}: {e}")
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"Dry run complete. Would migrate {completed_attempts.count()} attempts.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Migration complete. Migrated {migrated_count} attempts to submissions.")
            )