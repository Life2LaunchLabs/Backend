# management/commands/create_demo_from_json.py
import os
import json
from glob import glob
from typing import Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from apps.quests.models import (
    QuestTemplate, QuestItemDefinition, QuestTemplateItem, QuestEnrollment, QuestItemProgress, Activity, ActivityVersion, Page, Block, MediaAsset
)
from apps.organizations.models import Organization
from apps.users.models import User



DEFAULT_QUEST_DIR = os.path.join(
    settings.BASE_DIR, "demo", "quests"
)

DEFAULT_MEDIA_DIR = os.path.join(
    settings.BASE_DIR, "demo", "media"
)

DEFAULT_USERS_DIR = os.path.join(
    settings.BASE_DIR, "demo", "users"
)

DEFAULT_ORGS_DIR = os.path.join(
    settings.BASE_DIR, "demo", "organizations"
)

class Command(BaseCommand):
    help = "Create demo activities and assessments from JSON files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quest-dir",
            dest="quest_dir",
            default=DEFAULT_QUEST_DIR,
            help=f"Directory containing quest subdirectories (default: {DEFAULT_QUEST_DIR})",
        )
        parser.add_argument(
            "--users-dir",
            dest="users_dir",
            default=DEFAULT_USERS_DIR,
            help=f"Directory containing user JSON files (default: {DEFAULT_USERS_DIR})",
        )
        parser.add_argument(
            "--orgs-dir",
            dest="orgs_dir",
            default=DEFAULT_ORGS_DIR,
            help=f"Directory containing organization JSON files (default: {DEFAULT_ORGS_DIR})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse/validate only; do not write to DB.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail if referenced activities/users are missing. Otherwise warn and skip.",
        )

    def handle(self, *args, **opts):
        quest_dir = opts["quest_dir"]
        users_dir = opts["users_dir"]
        orgs_dir = opts["orgs_dir"]
        dry_run = opts["dry_run"]

        self.stdout.write(f"Reading demo content...")

        if not os.path.isdir(quest_dir):
            raise CommandError(f"Quest dir not found: {quest_dir}")

        # Process organizations from JSON files
        self._process_organizations(
            orgs_dir=orgs_dir,
            dry_run=dry_run,
        )

        # Process users from JSON files
        self._process_users(
            users_dir=users_dir,
            dry_run=dry_run,
        )

        # Process quests with new structure (each quest specifies its own org)
        self._process_quests(
            quest_dir=quest_dir,
            dry_run=dry_run,
            strict=opts["strict"],
        )

        # Process pending quest enrollments
        if hasattr(self, '_pending_enrollments') and not dry_run:
            self._process_quest_enrollments()

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes were made."))

    # --- helpers ---

    def _validate_activity_json(self, data: Dict[str, Any], file_name: str):
        """Basic validation with clear messages; keep it lightweight."""
        ctx = f"[{file_name}]"
        if "activity" not in data or "slug" not in data["activity"]:
            raise CommandError(f"{ctx} Missing activity.slug")
        if "version" not in data or "title" not in data["version"]:
            raise CommandError(f"{ctx} Missing version.title")
        if "pages" not in data or not isinstance(data["pages"], list):
            raise CommandError(f"{ctx} 'pages' must be a list")

        for i, page in enumerate(data["pages"]):
            if "index" not in page:
                raise CommandError(f"{ctx} Page #{i} missing 'index'")
            if "blocks" in page and not isinstance(page["blocks"], list):
                raise CommandError(f"{ctx} Page index {page.get('index')} 'blocks' must be a list")
            for j, block in enumerate(page.get("blocks", [])):
                if "index" not in block:
                    raise CommandError(f"{ctx} Page {page.get('index')} Block #{j} missing 'index'")
                if "block_type" not in block:
                    raise CommandError(f"{ctx} Page {page.get('index')} Block #{j} missing 'block_type'")
                if "config" in block and not isinstance(block["config"], dict):
                    raise CommandError(f"{ctx} Page {page.get('index')} Block #{j} 'config' must be an object")

    def _process_organizations(self, orgs_dir, dry_run: bool):
        """Process all organization JSON files."""
        self.stdout.write(f"\nProcessing organizations from: {orgs_dir}")

        if not os.path.isdir(orgs_dir):
            self.stdout.write(self.style.WARNING(f"Organizations dir not found: {orgs_dir}"))
            return

        org_paths = sorted(glob(os.path.join(orgs_dir, "*.json")))
        if not org_paths:
            self.stdout.write(self.style.WARNING("No organization JSON files found."))
            return

        self.stdout.write(f"Found {len(org_paths)} organization file(s)")

        # Parse and validate all organization files
        org_specs = []
        for p in org_paths:
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise CommandError(f"Invalid JSON in {p}: {e}") from e
            self._validate_organization_json(data, os.path.basename(p))
            org_specs.append((p, data))

        # Create organizations
        for p, org_data in org_specs:
            slug = org_data["slug"]

            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would create/update organization '{slug}'")
                continue

            with transaction.atomic():
                org, org_created = Organization.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'name': org_data.get('name', slug),
                        'description': org_data.get('description', ''),
                        'is_active': org_data.get('is_active', True),
                        'meta': org_data.get('meta', {}),
                    }
                )

                if not org_created:
                    # Update existing organization
                    org.name = org_data.get('name', org.name)
                    org.description = org_data.get('description', org.description)
                    org.is_active = org_data.get('is_active', org.is_active)
                    org.meta = org_data.get('meta', org.meta)
                    org.save()

                if org_created:
                    self.stdout.write(self.style.SUCCESS(f"  Created organization: {slug}"))
                else:
                    self.stdout.write(f"  Updated organization: {slug}")

    def _validate_organization_json(self, data: Dict[str, Any], file_name: str):
        """Validate organization JSON structure."""
        ctx = f"[{file_name}]"
        required = ["slug", "name"]
        for k in required:
            if k not in data:
                raise CommandError(f"{ctx} Missing required field '{k}'")

    def _process_users(self, users_dir, dry_run: bool):
        """Process all user JSON files and create users with their roles and enrollments."""
        self.stdout.write(f"\nProcessing users from: {users_dir}")

        if not os.path.isdir(users_dir):
            self.stdout.write(self.style.WARNING(f"Users dir not found: {users_dir}"))
            return

        user_paths = sorted(glob(os.path.join(users_dir, "*.json")))
        if not user_paths:
            self.stdout.write(self.style.WARNING("No user JSON files found."))
            return

        self.stdout.write(f"Found {len(user_paths)} user file(s)")

        # Parse and validate all user files
        user_specs = []
        for p in user_paths:
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise CommandError(f"Invalid JSON in {p}: {e}") from e
            self._validate_user_json(data, os.path.basename(p))
            user_specs.append((p, data))

        # Create users
        from apps.organizations.models import OrganizationAdmin

        for p, user_data in user_specs:
            email = user_data["email"]

            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would create/update user '{email}'")
                continue

            with transaction.atomic():
                # Create or update user
                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': user_data.get('first_name', ''),
                        'last_name': user_data.get('last_name', ''),
                        'bio': user_data.get('bio', ''),
                        'tagline': user_data.get('tagline', ''),
                    }
                )

                if not user_created:
                    # Update existing user
                    user.first_name = user_data.get('first_name', user.first_name)
                    user.last_name = user_data.get('last_name', user.last_name)
                    user.bio = user_data.get('bio', user.bio)
                    user.tagline = user_data.get('tagline', user.tagline)

                # Set password and staff status
                if 'password' in user_data:
                    user.set_password(user_data['password'])

                user.is_staff = user_data.get('is_staff', False)
                user.is_superuser = user_data.get('is_superuser', False)
                user.save()

                if user_created:
                    self.stdout.write(self.style.SUCCESS(
                        f"  Created user: {email} / password: {user_data.get('password', 'N/A')}"
                    ))
                else:
                    self.stdout.write(f"  Updated user: {email}")

                # Process organization roles
                for role_spec in user_data.get('organization_roles', []):
                    org_slug = role_spec.get('organization_slug')
                    role = role_spec.get('role', 'member')

                    # Get the organization
                    try:
                        target_org = Organization.objects.get(slug=org_slug)
                    except Organization.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"    Organization '{org_slug}' not found, skipping role assignment"
                        ))
                        continue

                    # Create or update organization role
                    org_admin, admin_created = OrganizationAdmin.objects.get_or_create(
                        user=user,
                        organization=target_org,
                        defaults={'role': role}
                    )
                    if not admin_created and org_admin.role != role:
                        org_admin.role = role
                        org_admin.save()

                    if admin_created:
                        self.stdout.write(f"    Added as {role} of {target_org.name}")
                    else:
                        self.stdout.write(f"    Already {role} of {target_org.name}")

                # Store quest enrollments for later (after quests are created)
                # We'll process these in a second pass
                if user_data.get('quest_enrollments'):
                    if not hasattr(self, '_pending_enrollments'):
                        self._pending_enrollments = []
                    self._pending_enrollments.append((user, user_data['quest_enrollments']))

    def _validate_user_json(self, data: Dict[str, Any], file_name: str):
        """Validate user JSON structure."""
        ctx = f"[{file_name}]"
        required = ["email", "first_name", "last_name"]
        for k in required:
            if k not in data:
                raise CommandError(f"{ctx} Missing required field '{k}'")

        if "organization_roles" in data and not isinstance(data["organization_roles"], list):
            raise CommandError(f"{ctx} 'organization_roles' must be a list")

        if "quest_enrollments" in data and not isinstance(data["quest_enrollments"], list):
            raise CommandError(f"{ctx} 'quest_enrollments' must be a list")

        for i, role in enumerate(data.get("organization_roles", [])):
            if "organization_slug" not in role:
                raise CommandError(f"{ctx} organization_roles[{i}] missing 'organization_slug'")

        for i, enrollment in enumerate(data.get("quest_enrollments", [])):
            if "quest_title" not in enrollment:
                raise CommandError(f"{ctx} quest_enrollments[{i}] missing 'quest_title'")

    def _process_quest_enrollments(self):
        """Process pending quest enrollments for users."""
        self.stdout.write(f"\nProcessing quest enrollments...")

        for user, enrollments in self._pending_enrollments:
            for enrollment_spec in enrollments:
                quest_title = enrollment_spec['quest_title']
                status = enrollment_spec.get('status', 'active')

                # Find the quest template (search across all organizations)
                try:
                    quest = QuestTemplate.objects.get(title=quest_title)
                except QuestTemplate.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  Quest '{quest_title}' not found for user {user.email}, skipping enrollment"
                    ))
                    continue
                except QuestTemplate.MultipleObjectsReturned:
                    # If multiple quests with same title, get the first one
                    quest = QuestTemplate.objects.filter(title=quest_title).first()
                    self.stdout.write(self.style.WARNING(
                        f"  Multiple quests found with title '{quest_title}', using first one"
                    ))

                with transaction.atomic():
                    enrollment, created = QuestEnrollment.objects.get_or_create(
                        quest_template=quest,
                        user=user,
                        defaults={'status': status}
                    )

                    if not created and enrollment.status != status:
                        enrollment.status = status
                        enrollment.save()

                    if created:
                        # Create progress records for all quest items
                        progress_records = QuestItemProgress.create_for_enrollment(enrollment)
                        self.stdout.write(self.style.SUCCESS(
                            f"  Enrolled {user.email} in '{quest.title}' with {len(progress_records)} items"
                        ))
                    else:
                        self.stdout.write(f"  User {user.email} already enrolled in '{quest.title}'")

    def _process_quests(self, quest_dir, dry_run: bool, strict: bool):
        """Process all quest directories in the quest_dir."""
        self.stdout.write(f"\nScanning quest directories in: {quest_dir}")

        # Find all subdirectories (each is a quest)
        quest_dirs = [d for d in glob(os.path.join(quest_dir, "*")) if os.path.isdir(d)]

        if not quest_dirs:
            self.stdout.write(self.style.WARNING("No quest directories found."))
            return

        self.stdout.write(f"Found {len(quest_dirs)} quest(s): {', '.join(os.path.basename(d) for d in quest_dirs)}")

        for quest_path in sorted(quest_dirs):
            quest_name = os.path.basename(quest_path)
            config_path = os.path.join(quest_path, "config.json")
            activities_dir = os.path.join(quest_path, "activities")

            if not os.path.exists(config_path):
                self.stdout.write(self.style.WARNING(f"Skipping '{quest_name}': no config.json found"))
                continue

            self.stdout.write(f"\nProcessing quest: {quest_name}")

            # Load quest config
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    quest_config = json.load(f)
                except json.JSONDecodeError as e:
                    raise CommandError(f"Invalid JSON in {config_path}: {e}") from e

            self._validate_quest_json(quest_config, f"{quest_name}/config.json")

            # Get the organization for this quest
            org_slug = quest_config.get("organization_slug")
            try:
                org = Organization.objects.get(slug=org_slug)
            except Organization.DoesNotExist:
                msg = f"Organization '{org_slug}' not found for quest '{quest_name}'"
                if strict:
                    raise CommandError(msg)
                self.stdout.write(self.style.WARNING(msg + " — skipping this quest."))
                continue

            # Get the creator user (required)
            created_by_email = quest_config.get("created_by_email")
            if not created_by_email:
                msg = f"Quest '{quest_name}' missing required field 'created_by_email'"
                raise CommandError(msg)

            try:
                creator = User.objects.get(email=created_by_email)
            except User.DoesNotExist:
                msg = f"User '{created_by_email}' not found for quest '{quest_name}'"
                if strict:
                    raise CommandError(msg)
                self.stdout.write(self.style.WARNING(msg + " — skipping this quest."))
                continue

            # Process activities for this quest
            activity_slugs = self._process_quest_activities(
                activities_dir=activities_dir,
                quest_name=quest_name,
                org=org,
                dry_run=dry_run,
            )

            # Create the quest template
            self._create_quest_template(
                quest_config=quest_config,
                quest_name=quest_name,
                activity_slugs=activity_slugs,
                org=org,
                creator=creator,
                dry_run=dry_run,
                strict=strict,
            )

    def _process_quest_activities(self, activities_dir, quest_name, org, dry_run: bool):
        """Process all activity JSON files in a quest's activities directory."""
        if not os.path.isdir(activities_dir):
            self.stdout.write(self.style.WARNING(f"  No activities directory found for quest '{quest_name}'"))
            return []

        activity_paths = sorted(glob(os.path.join(activities_dir, "*.json")))
        if not activity_paths:
            self.stdout.write(self.style.WARNING(f"  No activity JSON files found for quest '{quest_name}'"))
            return []

        self.stdout.write(f"  Found {len(activity_paths)} activity file(s)")

        # Parse all activity files
        activities_data: Dict[str, Dict[str, Any]] = {}
        for p in activity_paths:
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise CommandError(f"Invalid JSON in {p}: {e}") from e
                self._validate_activity_json(data, file_name=os.path.basename(p))
                activities_data[p] = data

        # Collect media assets from all activities
        media_index: Dict[str, Dict[str, Any]] = {}
        for data in activities_data.values():
            for m in data.get("media_assets", []):
                media_index[m["filename"]] = m

        # Create media assets
        from apps.quests.services import MediaService
        media_objects: Dict[str, MediaAsset] = {}

        if media_index:
            self.stdout.write(f"  Processing {len(media_index)} media asset(s)...")

        for filename, spec in media_index.items():
            media_filename = spec.get("path", filename)
            if "/" in media_filename:
                media_filename = os.path.basename(media_filename)

            demo_media_path = os.path.join(DEFAULT_MEDIA_DIR, media_filename)

            if not os.path.exists(demo_media_path):
                self.stdout.write(self.style.WARNING(f"    Media file not found: {demo_media_path}"))
                continue

            if dry_run:
                self.stdout.write(f"    [DRY RUN] Would create MediaAsset for: {filename}")
                continue

            with open(demo_media_path, 'rb') as f:
                file_content = f.read()

            meta = {
                "title": spec.get("title", filename),
                "description": spec.get("description", ""),
                "alt_text": spec.get("alt_text", spec.get("description", "")),
            }

            asset = MediaService.create_media_asset(
                file_content=file_content,
                filename=filename,
                meta=meta,
                organization_id=str(org.id)
            )

            media_objects[filename] = asset
            self.stdout.write(f"    Created MediaAsset: {spec.get('title', filename)}")

        # Create activities
        created_slugs = []
        for p, data in activities_data.items():
            slug = data["activity"]["slug"]

            with transaction.atomic():
                if dry_run:
                    self.stdout.write(f"    [DRY RUN] Would create/update activity '{slug}'")
                    created_slugs.append(slug)
                else:
                    activity, created = Activity.objects.get_or_create(
                        slug=slug,
                        defaults={
                            "status": data["activity"].get("status", "published"),
                            "organization": org,
                        },
                    )
                    if not created:
                        if activity.organization_id != org.id:
                            activity.organization = org
                        if "status" in data["activity"]:
                            activity.status = data["activity"]["status"]
                        activity.save()

                    # Replace all versions
                    activity.versions.all().delete()

                    version = ActivityVersion.objects.create(
                        activity=activity,
                        version=data["version"].get("number", 1),
                        title=data["version"]["title"],
                        description=data["version"].get("description", ""),
                        meta=data["version"].get("meta", {}),
                        is_published=data["version"].get("is_published", True),
                    )

                    # Create pages & blocks
                    for page_spec in sorted(data["pages"], key=lambda x: x.get("index", 0)):
                        page = Page.objects.create(
                            activity_version=version,
                            index=page_spec["index"],
                            title=page_spec.get("title", ""),
                            meta=page_spec.get("meta", {}),
                        )

                        for block_spec in sorted(page_spec.get("blocks", []), key=lambda x: x.get("index", 0)):
                            config = dict(block_spec.get("config", {}))

                            if block_spec["block_type"] == "media":
                                media_filename = config.pop("media_filename", None)
                                if media_filename and media_filename in media_objects:
                                    config["media_id"] = str(media_objects[media_filename].id)

                            Block.objects.create(
                                page=page,
                                index=block_spec["index"],
                                block_type=block_spec["block_type"],
                                config=config,
                            )

                    created_slugs.append(slug)
                    self.stdout.write(f"    Created activity: {slug}")

        return created_slugs

    def _create_quest_template(self, quest_config, quest_name, activity_slugs, org, creator, dry_run: bool, strict: bool):
        """Create a quest template from config and activities."""
        title = quest_config["title"]

        # Pre-check activities exist
        item_slugs = [it["activity_slug"] for it in quest_config.get("items", [])]
        slug_to_activity = {a.slug: a for a in Activity.objects.filter(slug__in=item_slugs, organization=org)}
        missing = [s for s in item_slugs if s not in slug_to_activity]

        if missing:
            msg = f"Quest '{title}' references missing activities: {', '.join(missing)}"
            if strict:
                raise CommandError(msg)
            self.stdout.write(self.style.WARNING(msg + " — skipping this quest."))
            return

        if dry_run:
            self.stdout.write(f"  [DRY RUN] Would recreate quest '{title}' with {len(item_slugs)} items.")
            return

        with transaction.atomic():
            # Delete existing with same title+org
            existing = QuestTemplate.objects.filter(title=title, organization=org).first()
            if existing:
                self.stdout.write(self.style.WARNING(f"  Quest '{title}' already exists; deleting to recreate..."))
                existing.delete()

            quest = QuestTemplate.objects.create(
                title=title,
                description=quest_config.get("description", ""),
                color=quest_config.get("color", "#4CAF50"),
                category=quest_config.get("category", "Introduction"),
                organization=org,
                created_by=creator,
                is_public=quest_config.get("is_public", True),
                is_template=quest_config.get("is_template", True),
                status=quest_config.get("status", "published"),
                meta=quest_config.get("meta", {}),
            )
            self.stdout.write(f"  Created quest: {quest.title}")

            # Create item definitions and template items
            item_defs = []
            for item in quest_config.get("items", []):
                activity = slug_to_activity[item["activity_slug"]]
                latest_version = activity.versions.filter(is_published=True).order_by("-version").first()

                item_def = QuestItemDefinition.objects.create(
                    item_type="activity",
                    title=(latest_version.title if latest_version else activity.slug),
                    description=(latest_version.description if latest_version else "Interactive learning activity"),
                    estimated_duration_days=item.get("estimated_duration_days", 7),
                    activity=activity,
                    organization=org,
                )
                item_defs.append(item_def)
                self.stdout.write(f"    Item def: {item_def.title}")

            # Create QuestTemplateItems in order
            index_to_qti = {}
            for order, item_def in enumerate(item_defs):
                qti = QuestTemplateItem.objects.create(
                    quest_template=quest,
                    item_definition=item_def,
                    order=order,
                    notes=quest_config["items"][order].get("notes", ""),
                )
                index_to_qti[order] = qti

            # Apply prerequisites
            for order, spec in enumerate(quest_config.get("items", [])):
                qti = index_to_qti[order]
                prereq_indexes = spec.get("prerequisites", [])
                if prereq_indexes:
                    for pi in prereq_indexes:
                        if pi in index_to_qti:
                            qti.prerequisites.add(index_to_qti[pi])
                elif order > 0:
                    qti.prerequisites.add(index_to_qti[order - 1])

            quest.update_estimated_total_days()
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Finished quest '{quest.title}' with {len(item_defs)} items; total days: {quest.estimated_total_days}"
                )
            )

    def _validate_quest_json(self, data, file_name: str):
        ctx = f"[{file_name}]"
        required_top = ["title", "items", "organization_slug"]
        for k in required_top:
            if k not in data:
                raise CommandError(f"{ctx} Missing '{k}'")
        if not isinstance(data["items"], list) or not data["items"]:
            raise CommandError(f"{ctx} 'items' must be a non-empty list")
        for i, it in enumerate(data["items"]):
            if "activity_slug" not in it:
                raise CommandError(f"{ctx} items[{i}] missing 'activity_slug'")
            if "estimated_duration_days" in it and not isinstance(it["estimated_duration_days"], int):
                raise CommandError(f"{ctx} items[{i}].estimated_duration_days must be an integer if provided")
            if "prerequisites" in it and not all(isinstance(x, int) for x in it["prerequisites"]):
                raise CommandError(f"{ctx} items[{i}].prerequisites must be a list of item indexes")
