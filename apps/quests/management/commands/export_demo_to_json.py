# apps/quests/management/commands/export_demo_to_json.py
import os
import json
from typing import Dict, Any, List

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.quests.models import (
    QuestTemplate, QuestTemplateItem, Activity, ActivityVersion, Page, Block, MediaAsset
)
from apps.organizations.models import Organization


DEFAULT_ACTIVITIES_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "activities"
)

DEFAULT_QUESTS_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "quests"
)

DEFAULT_MEDIA_DIR = os.path.join(
    settings.BASE_DIR, "apps", "quests", "demo", "media"
)


class Command(BaseCommand):
    help = "Export activities and quests from database back to JSON files (for demo updates)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-slug",
            dest="org_slug",
            default="life2launch",
            help="Organization slug to export activities from (default: life2launch)",
        )
        parser.add_argument(
            "--quest-id",
            dest="quest_id",
            help="Specific quest ID to export (optional - exports all if not specified)",
        )

    def handle(self, *args, **opts):
        org_slug = opts["org_slug"]
        quest_id = opts.get("quest_id")

        activities_dir = DEFAULT_ACTIVITIES_DIR
        quests_dir = DEFAULT_QUESTS_DIR

        # Clear existing JSON files in demo directories
        self.stdout.write(self.style.WARNING("Clearing existing demo files..."))

        # Remove all JSON files from activities directory
        if os.path.exists(activities_dir):
            for filename in os.listdir(activities_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(activities_dir, filename))
                    self.stdout.write(f"  Removed {filename}")

        # Remove all JSON files from quests directory
        if os.path.exists(quests_dir):
            for filename in os.listdir(quests_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(quests_dir, filename))
                    self.stdout.write(f"  Removed {filename}")

        # Clear media directory
        media_dir = DEFAULT_MEDIA_DIR
        if os.path.exists(media_dir):
            for filename in os.listdir(media_dir):
                if filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                    os.remove(os.path.join(media_dir, filename))
                    self.stdout.write(f"  Removed media: {filename}")

        # Create directories if they don't exist
        os.makedirs(activities_dir, exist_ok=True)
        os.makedirs(quests_dir, exist_ok=True)
        os.makedirs(media_dir, exist_ok=True)

        self.stdout.write(f"\nExporting to demo directories...")

        # Get organization
        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist:
            raise CommandError(f"Organization with slug '{org_slug}' not found.")

        # Export quests
        if quest_id:
            quests = QuestTemplate.objects.filter(id=quest_id, organization=org)
            if not quests.exists():
                raise CommandError(f"Quest with ID '{quest_id}' not found in organization '{org_slug}'")
        else:
            quests = QuestTemplate.objects.filter(organization=org)

        self.stdout.write(f"Found {quests.count()} quest(s) to export")

        # Track which activities to export
        activities_to_export = set()

        for quest in quests:
            quest_data = self._export_quest(quest)

            # Save quest JSON with simplified filename
            # "Getting Started with Life2Launch" -> "getting-started.json"
            title_parts = quest.title.lower().split()
            # Take first 2-3 meaningful words
            simple_name = '-'.join(title_parts[:2]) if len(title_parts) >= 2 else title_parts[0]
            quest_filename = f"{simple_name}.json"
            quest_path = os.path.join(quests_dir, quest_filename)
            with open(quest_path, 'w', encoding='utf-8') as f:
                json.dump(quest_data, f, indent=2, ensure_ascii=False)
            self.stdout.write(f"  Exported quest: {quest_path}")

            # Track activities used in this quest
            for item in quest.template_items.all():
                if item.item_definition.item_type == 'activity' and item.item_definition.activity:
                    activities_to_export.add(item.item_definition.activity)

        # Export activities
        self.stdout.write(f"\nExporting {len(activities_to_export)} activities...")

        # Also include any activities from the org not in quests
        all_org_activities = Activity.objects.filter(organization=org, status='published')
        for activity in all_org_activities:
            activities_to_export.add(activity)

        for activity in activities_to_export:
            activity_data = self._export_activity(activity)

            # Save activity JSON
            activity_filename = f"{activity.slug}.json"
            activity_path = os.path.join(activities_dir, activity_filename)
            with open(activity_path, 'w', encoding='utf-8') as f:
                json.dump(activity_data, f, indent=2, ensure_ascii=False)
            self.stdout.write(f"  Exported activity: {activity_path}")

        self.stdout.write(self.style.SUCCESS(f"\n✓ Export complete!"))
        self.stdout.write(f"  Activities: {activities_dir}")
        self.stdout.write(f"  Quests: {quests_dir}")

    def _export_quest(self, quest: QuestTemplate) -> Dict[str, Any]:
        """Export a quest template to JSON format matching the import format."""
        quest_data = {
            "title": quest.title,
            "description": quest.description,
            "color": quest.color or "#4CAF50",
            "category": quest.category or "General",
            "status": "published",
            "is_public": True,
            "is_template": True,
            "meta": {},
            "items": []
        }

        # Add items
        for item in quest.template_items.all().select_related('item_definition__activity').order_by('order'):
            item_data = {}

            if item.item_definition.item_type == 'activity' and item.item_definition.activity:
                item_data["activity_slug"] = item.item_definition.activity.slug
            elif item.item_definition.item_type == 'milestone':
                item_data["milestone_data"] = item.item_definition.milestone_data

            # Add duration (use override if set, otherwise use item definition's estimated duration)
            duration = item.override_duration_days or item.item_definition.estimated_duration_days
            item_data["estimated_duration_days"] = duration

            # Add notes only if not empty
            if item.notes and item.notes.strip():
                item_data["notes"] = item.notes

            quest_data["items"].append(item_data)

        return quest_data

    def _export_activity(self, activity: Activity) -> Dict[str, Any]:
        """Export an activity to JSON format matching the import format."""
        # Get latest published version
        version = activity.versions.filter(is_published=True).order_by('-version').first()
        if not version:
            raise CommandError(f"Activity '{activity.slug}' has no published version")

        # Collect media assets used in this activity
        media_assets = {}

        # Build activity data
        activity_data = {
            "activity": {
                "slug": activity.slug,
                "status": activity.status,
            },
            "version": {
                "title": version.title,
                "description": version.description,
                "meta": version.meta,
            },
            "media_assets": [],
            "pages": []
        }

        # Process pages
        for page in version.pages.all().order_by('index'):
            page_data = {
                "index": page.index,
                "title": page.title,
                "meta": page.meta,
                "blocks": []
            }

            # Process blocks
            for block in page.blocks.all().order_by('index'):
                block_data = {
                    "index": block.index,
                    "block_type": block.block_type,
                    "config": dict(block.config)
                }

                # If block has media_id, convert it to media_filename and track the asset
                if block.block_type == 'media' and 'media_id' in block.config:
                    media_id = block.config['media_id']
                    try:
                        media = MediaAsset.objects.get(id=media_id)
                        # Generate a simple filename from the media ID
                        filename = self._get_media_filename(media)
                        block_data['config']['media_filename'] = filename
                        del block_data['config']['media_id']  # Remove media_id from export
                        media_assets[filename] = media
                        # Export the media file to demo/media directory
                        self._export_media_file(media, filename)
                    except MediaAsset.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Media asset {media_id} not found"))

                page_data["blocks"].append(block_data)

            activity_data["pages"].append(page_data)

        # Add media assets section
        for filename, media in media_assets.items():
            activity_data["media_assets"].append({
                "filename": filename,
                "path": filename,  # Simplified path
                "title": media.meta.get('title', filename),
                "description": media.meta.get('description', ''),
                "mime_type": media.mime_type,
                "alt_text": media.meta.get('alt_text', media.meta.get('description', ''))
            })

        return activity_data

    def _get_media_filename(self, media: MediaAsset) -> str:
        """Generate a simple filename for a media asset using its ID."""
        # Use extension from storage_key or mime_type
        ext = os.path.splitext(media.storage_key)[1] or '.png'
        return f"{media.id}{ext}"

    def _export_media_file(self, media: MediaAsset, filename: str) -> None:
        """Export a media file from storage to the demo/media directory."""
        from django.core.files.storage import default_storage

        media_dir = DEFAULT_MEDIA_DIR
        dest_path = os.path.join(media_dir, filename)

        try:
            # Read from storage
            if default_storage.exists(media.storage_key):
                with default_storage.open(media.storage_key, 'rb') as source_file:
                    file_content = source_file.read()

                # Write to demo/media directory
                with open(dest_path, 'wb') as dest_file:
                    dest_file.write(file_content)

                self.stdout.write(f"  Exported media: {filename}")
            else:
                self.stdout.write(self.style.WARNING(f"  Media file not found in storage: {media.storage_key}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Failed to export media {filename}: {e}"))
