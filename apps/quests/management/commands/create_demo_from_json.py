# apps/quests/management/commands/create_demo_from_json.py
import os
import json
from glob import glob
from typing import Dict, Any, List

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from apps.quests.models import (
    QuestTemplate, QuestItemDefinition, QuestTemplateItem, QuestEnrollment, QuestItemProgress, Activity, ActivityVersion, Page, Block, MediaAsset
)
from apps.organizations.models import Organization
from apps.users.models import User



DEFAULT_DEMO_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "activities"
)

# add near DEFAULT_DEMO_DIR
DEFAULT_QUEST_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "quests"
)

DEFAULT_MEDIA_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "media"
)

class Command(BaseCommand):
    help = "Create demo activities and assessments from JSON files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo-dir",
            dest="demo_dir",
            default=DEFAULT_DEMO_DIR,
            help=f"Directory containing *.json activity files (default: {DEFAULT_DEMO_DIR})",
        )
        parser.add_argument(
            "--org-slug",
            dest="org_slug",
            default="life2launch",
            help="Organization slug to attach activities to (default: life2launch)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse/validate only; do not write to DB.",
        )

        parser.add_argument(
            "--quest-dir",
            dest="quest_dir",
            default=DEFAULT_QUEST_DIR,
            help=f"Directory containing *.json quest files (default: {DEFAULT_QUEST_DIR})",
        )
        parser.add_argument(
            "--creator-email",
            dest="creator_email",
            default="sam@fake.com",
            help="Email of the User to set as quest.created_by (default: sam@fake.com)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail if referenced activities/users are missing. Otherwise warn and skip.",
        )

    def handle(self, *args, **opts):
        demo_dir = opts["demo_dir"]
        org_slug = opts["org_slug"]
        dry_run = opts["dry_run"]
        creator_email = opts["creator_email"]

        self.stdout.write(f"Reading demo activities from: {demo_dir}")

        if not os.path.isdir(demo_dir):
            raise CommandError(f"Demo dir not found: {demo_dir}")

        # Create or get organization
        org, org_created = Organization.objects.get_or_create(
            slug=org_slug,
            defaults={
                'name': 'Life2Launch',
                'description': 'Default organization for demo content'
            }
        )
        if org_created:
            self.stdout.write(self.style.SUCCESS(f"Created organization: {org_slug}"))
        else:
            self.stdout.write(f"Using existing organization: {org_slug}")

        # Create or get demo user
        user, user_created = User.objects.get_or_create(
            email=creator_email,
            defaults={
                'first_name': 'Sam',
                'last_name': 'Garcia',
                'bio': "I'm redefining human centered design in a high tech era. Open to work helping your business with branding, marketing, and social media.",
                'tagline': "Visionary designer and recent high school graduate"
            }
        )
        if user_created:
            user.set_password('samgarcia')
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created demo user: {creator_email} / password: samgarcia"))
        else:
            self.stdout.write(f"Using existing user: {creator_email}")

        # Add user as admin of organization
        from apps.organizations.models import OrganizationAdmin
        org_admin, admin_created = OrganizationAdmin.objects.get_or_create(
            user=user,
            organization=org,
            defaults={'role': 'admin'}
        )
        if admin_created:
            self.stdout.write(self.style.SUCCESS(f"Added {user.email} as admin of {org.name}"))
        else:
            self.stdout.write(f"User {user.email} is already admin of {org.name}")

        # Load JSON files
        paths = sorted(glob(os.path.join(demo_dir, "*.json")))
        if not paths:
            self.stdout.write(self.style.WARNING("No *.json files found. Nothing to do."))
            return

        self.stdout.write(f"Found {len(paths)} file(s): " + ", ".join(os.path.basename(p) for p in paths))

        # Parse into memory first (fail fast if any file is invalid)
        data_by_file: Dict[str, Dict[str, Any]] = {}
        for p in paths:
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise CommandError(f"Invalid JSON in {p}: {e}") from e
                self._validate_activity_json(data, file_name=os.path.basename(p))
                data_by_file[p] = data

        # Create MediaAssets up-front (from any file that declares them)
        # We aggregate a filename->definition map; last definition wins if duplicates
        media_index: Dict[str, Dict[str, Any]] = {}
        for data in data_by_file.values():
            for m in data.get("media_assets", []):
                media_index[m["filename"]] = m

        if media_index:
            self.stdout.write(f"Processing {len(media_index)} media asset(s)...")

        from apps.quests.services import MediaService

        media_objects: Dict[str, MediaAsset] = {}
        for filename, spec in media_index.items():
            # Look for media in demo/media directory instead of MEDIA_ROOT
            media_filename = spec.get("path", filename)
            # Strip any leading path components to get just the filename
            if "/" in media_filename:
                media_filename = os.path.basename(media_filename)

            demo_media_path = os.path.join(DEFAULT_MEDIA_DIR, media_filename)

            if not os.path.exists(demo_media_path):
                self.stdout.write(self.style.WARNING(f"Media file not found: {demo_media_path}"))
                continue

            if dry_run:
                self.stdout.write(f"[DRY RUN] Would create MediaAsset for: {filename}")
                continue

            # Read the existing file from demo/media directory
            with open(demo_media_path, 'rb') as f:
                file_content = f.read()

            # Create media asset using MediaService with new path structure
            meta = {
                "title": spec.get("title", filename),
                "description": spec.get("description", ""),
                "alt_text": spec.get("alt_text", spec.get("description", "")),
            }

            # Use MediaService to create with new path pattern
            asset = MediaService.create_media_asset(
                file_content=file_content,
                filename=filename,
                meta=meta,
                organization_id=str(org.id)
            )

            media_objects[filename] = asset
            self.stdout.write(f"Created MediaAsset: {spec.get('title', filename)} at {asset.storage_key}")

        created_activities: List[str] = []

        # Apply activities
        for p, data in data_by_file.items():
            slug = data["activity"]["slug"]
            with transaction.atomic():
                if dry_run:
                    self.stdout.write(f"[DRY RUN] Would create/update activity '{slug}'")
                else:
                    activity, created = Activity.objects.get_or_create(
                        slug=slug,
                        defaults={
                            "status": data["activity"].get("status", "published"),
                            "organization": org,
                        },
                    )
                    if not created:
                        # Ensure organization matches and status is updated if provided
                        if activity.organization_id != org.id:
                            activity.organization = org
                        if "status" in data["activity"]:
                            activity.status = data["activity"]["status"]
                        activity.save()

                    # Replace all versions to match the JSON (like your current command)
                    activity.versions.all().delete()

                    version = ActivityVersion.objects.create(
                        activity=activity,
                        version=data["version"].get("number", 1),
                        title=data["version"]["title"],
                        description=data["version"].get("description", ""),
                        meta=data["version"].get("meta", {}),
                        is_published=data["version"].get("is_published", True),
                    )

                    # Pages & Blocks
                    for page_spec in sorted(data["pages"], key=lambda x: x.get("index", 0)):
                        page = Page.objects.create(
                            activity_version=version,
                            index=page_spec["index"],
                            title=page_spec.get("title", ""),
                            meta=page_spec.get("meta", {}),
                        )

                        for block_spec in sorted(page_spec.get("blocks", []), key=lambda x: x.get("index", 0)):
                            config = dict(block_spec.get("config", {}))

                            # If block is 'media' and references a filename, resolve to id
                            if block_spec["block_type"] == "media":
                                # Allow either a raw 'media_id' or a friendly 'media_filename'
                                media_filename = config.pop("media_filename", None)
                                if media_filename and media_filename in media_objects:
                                    config["media_id"] = str(media_objects[media_filename].id)

                            Block.objects.create(
                                page=page,
                                index=block_spec["index"],
                                block_type=block_spec["block_type"],
                                config=config,
                            )

                    created_activities.append(slug)
                    self.stdout.write(self.style.SUCCESS(f"Created demo activity: {slug}"))

        self._create_quests_from_json(
            quest_dir=opts["quest_dir"],
            org=org,
            creator_email=opts["creator_email"],
            dry_run=dry_run,
            strict=opts["strict"],
        )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes were made."))
        else:
            if created_activities:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully created {len(created_activities)} demo activities: {', '.join(created_activities)}"
                    )
                )

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
                
    def _create_quests_from_json(self, quest_dir, org, creator_email, dry_run: bool, strict: bool):
        self.stdout.write(f"Reading quests from: {quest_dir}")
        if not os.path.isdir(quest_dir):
            self.stdout.write(self.style.WARNING(f"Quest dir not found: {quest_dir}"))
            return

        paths = sorted(glob(os.path.join(quest_dir, "*.json")))
        if not paths:
            self.stdout.write(self.style.WARNING("No quest *.json files found. Skipping quests."))
            return

        # resolve creator
        creator = None
        if creator_email:
            try:
                creator = User.objects.get(email=creator_email)
            except User.DoesNotExist:
                msg = f"User with email '{creator_email}' not found"
                if strict:
                    raise CommandError(msg)
                self.stdout.write(self.style.WARNING(msg + " — created_by will be null."))

        # parse & validate first
        quest_specs = []
        for p in paths:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._validate_quest_json(data, os.path.basename(p))
            quest_specs.append((p, data))

        # create quests
        for p, qdata in quest_specs:
            title = qdata["title"]
            self.stdout.write(f"Processing quest: {title}")

            # pre-check activities exist
            slugs = [it["activity_slug"] for it in qdata.get("items", [])]
            slug_to_activity = {a.slug: a for a in Activity.objects.filter(slug__in=slugs, organization=org)}
            missing = [s for s in slugs if s not in slug_to_activity]
            if missing:
                msg = f"Quest '{title}' references missing activities: {', '.join(missing)}"
                if strict:
                    raise CommandError(msg)
                self.stdout.write(self.style.WARNING(msg + " — skipping this quest."))
                continue

            if dry_run:
                self.stdout.write(f"[DRY RUN] Would recreate quest '{title}' with {len(slugs)} items.")
                continue

            with transaction.atomic():
                # delete existing with same title+org (matches your prior behavior)
                existing = QuestTemplate.objects.filter(title=title, organization=org).first()
                if existing:
                    self.stdout.write(self.style.WARNING(f"Quest '{title}' already exists (ID: {existing.id}); deleting to recreate..."))
                    existing.delete()

                quest = QuestTemplate.objects.create(
                    title=title,
                    description=qdata.get("description", ""),
                    color=qdata.get("color", "#4CAF50"),
                    category=qdata.get("category", "Introduction"),
                    organization=org,
                    created_by=creator,
                    is_public=qdata.get("is_public", True),
                    is_template=qdata.get("is_template", True),
                    status=qdata.get("status", "published"),
                    meta=qdata.get("meta", {}),
                )
                self.stdout.write(f"  Created quest: {quest.title}")

                # item defs + items (ordered)
                item_defs = []
                for idx, item in enumerate(qdata.get("items", [])):
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

                # create QuestTemplateItems in order and add prerequisites
                index_to_qti = {}
                for order, item_def in enumerate(item_defs):
                    qti = QuestTemplateItem.objects.create(
                        quest_template=quest,
                        item_definition=item_def,
                        order=order,
                        notes=qdata["items"][order].get("notes", ""),
                    )
                    index_to_qti[order] = qti
                    self.stdout.write(f"    Added to quest at position {order}: {item_def.title}")

                # apply prerequisites:
                # 1) explicit prerequisites by item index (optional)
                # 2) fallback chain to previous item if not provided
                for order, spec in enumerate(qdata.get("items", [])):
                    qti = index_to_qti[order]
                    prereq_indexes = spec.get("prerequisites", [])
                    if prereq_indexes:
                        for pi in prereq_indexes:
                            if pi in index_to_qti:
                                qti.prerequisites.add(index_to_qti[pi])
                    elif order > 0:
                        # default chain behavior
                        qti.prerequisites.add(index_to_qti[order - 1])

                quest.update_estimated_total_days()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Finished quest '{quest.title}' with {len(item_defs)} items; total days: {quest.estimated_total_days}"
                    )
                )

                # Enroll the creator user in this demo quest
                if creator:
                    enrollment, created = QuestEnrollment.objects.get_or_create(
                        quest_template=quest,
                        user=creator,
                        defaults={
                            'status': 'active'
                        }
                    )
                    if created:
                        # Create progress records for all quest items
                        progress_records = QuestItemProgress.create_for_enrollment(enrollment)
                        self.stdout.write(self.style.SUCCESS(
                            f"  Enrolled user '{creator.email}' in quest '{quest.title}' with {len(progress_records)} items"
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(f"  User '{creator.email}' already enrolled in quest '{quest.title}'"))

    def _validate_quest_json(self, data, file_name: str):
        ctx = f"[{file_name}]"
        required_top = ["title", "items"]
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
