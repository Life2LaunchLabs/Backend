# apps/quests/management/commands/create_demo_from_json.py
import os
import json
from glob import glob
from typing import Dict, Any, List

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from apps.quests.models import (
    QuestTemplate, QuestItemDefinition, QuestTemplateItem, Activity, ActivityVersion, Page, Block, MediaAsset
)
from apps.organizations.models import Organization
from apps.users.models import User



DEFAULT_DEMO_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "activities"
)

# add near DEFAULT_DEMO_DIR
DEFAULT_QUEST_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "quest"
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

        self.stdout.write(f"Reading demo activities from: {demo_dir}")

        if not os.path.isdir(demo_dir):
            raise CommandError(f"Demo dir not found: {demo_dir}")

        # Get org
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            raise CommandError(
                f"Organization with slug '{org_slug}' not found. "
                "Please create it (e.g., run create_default_admin_user)."
            )

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
        media_objects: Dict[str, MediaAsset] = {}
        for filename, spec in media_index.items():
            storage_key = spec["path"]  # relative path under MEDIA_ROOT
            full_path = os.path.join(settings.MEDIA_ROOT, storage_key)
            if not os.path.exists(full_path):
                self.stdout.write(self.style.WARNING(f"Media file not found: {full_path}"))
                # We still create the record if file absent? Keep prior behavior: only create if exists.
                continue

            if dry_run:
                self.stdout.write(f"[DRY RUN] Would ensure MediaAsset for: {storage_key}")
                continue

            asset, created = MediaAsset.objects.get_or_create(
                storage_key=storage_key,
                defaults={
                    "mime_type": spec.get("mime_type", "image/png"),
                    "meta": {
                        "title": spec.get("title", filename),
                        "description": spec.get("description", ""),
                        "alt_text": spec.get("alt_text", spec.get("description", "")),
                    },
                },
            )
            media_objects[filename] = asset
            msg = "Created" if created else "Found existing"
            self.stdout.write(f"{msg} MediaAsset: {spec.get('title', filename)}")

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
                        notes=qdata["items"][order].get("notes", "Complete this activity to progress in your journey"),
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
