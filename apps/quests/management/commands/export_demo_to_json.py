# apps/quests/management/commands/export_demo_to_json.py
import os
import json
import shutil
import re
from typing import Dict, Any, Set

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.quests.models import (
    QuestTemplate, QuestTemplateItem, QuestEnrollment, Activity, ActivityVersion, Page, Block, MediaAsset
)
from apps.organizations.models import Organization, OrganizationAdmin
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
    help = "Export organizations, users, quests, and activities from database back to JSON files (for demo updates)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-slug",
            dest="org_slug",
            help="Specific organization slug to export (optional - exports all if not specified)",
        )
        parser.add_argument(
            "--quest-id",
            dest="quest_id",
            help="Specific quest ID to export (optional - exports all if not specified)",
        )
        parser.add_argument(
            "--quest-dir",
            dest="quest_dir",
            default=DEFAULT_QUEST_DIR,
            help=f"Directory to export quests to (default: {DEFAULT_QUEST_DIR})",
        )
        parser.add_argument(
            "--users-dir",
            dest="users_dir",
            default=DEFAULT_USERS_DIR,
            help=f"Directory to export users to (default: {DEFAULT_USERS_DIR})",
        )
        parser.add_argument(
            "--orgs-dir",
            dest="orgs_dir",
            default=DEFAULT_ORGS_DIR,
            help=f"Directory to export organizations to (default: {DEFAULT_ORGS_DIR})",
        )

    def handle(self, *args, **opts):
        org_slug = opts.get("org_slug")
        quest_id = opts.get("quest_id")
        quest_dir = opts["quest_dir"]
        users_dir = opts["users_dir"]
        orgs_dir = opts["orgs_dir"]

        # Clear existing demo directories
        self.stdout.write(self.style.WARNING("Clearing existing demo files..."))
        self._clear_demo_directories(quest_dir, users_dir, orgs_dir)

        # Create directories
        os.makedirs(quest_dir, exist_ok=True)
        os.makedirs(users_dir, exist_ok=True)
        os.makedirs(orgs_dir, exist_ok=True)
        os.makedirs(DEFAULT_MEDIA_DIR, exist_ok=True)

        self.stdout.write(f"\nExporting demo data...")

        # Determine which organizations to export
        if org_slug:
            try:
                organizations = [Organization.objects.get(slug=org_slug)]
            except Organization.DoesNotExist:
                raise CommandError(f"Organization with slug '{org_slug}' not found.")
        else:
            organizations = list(Organization.objects.all())

        self.stdout.write(f"Found {len(organizations)} organization(s) to export")

        # Track users and quests across all organizations
        all_users: Set[User] = set()
        all_quests = []

        # Export organizations
        self._export_organizations(organizations, orgs_dir)

        # Process each organization
        for org in organizations:
            # Get quests for this organization
            if quest_id:
                quests = QuestTemplate.objects.filter(id=quest_id, organization=org)
                if not quests.exists():
                    raise CommandError(f"Quest with ID '{quest_id}' not found in organization '{org.slug}'")
            else:
                quests = QuestTemplate.objects.filter(organization=org)

            all_quests.extend(quests)

            # Collect users associated with this org (admins and enrolled users)
            org_admins = OrganizationAdmin.objects.filter(organization=org).select_related('user')
            for admin in org_admins:
                all_users.add(admin.user)

            # Collect users enrolled in quests
            for quest in quests:
                enrollments = QuestEnrollment.objects.filter(quest_template=quest).select_related('user')
                for enrollment in enrollments:
                    all_users.add(enrollment.user)

        # Export quests with their activities
        self._export_quests(all_quests, quest_dir)

        # Export users with their roles and enrollments
        self._export_users(all_users, users_dir)

        self.stdout.write(self.style.SUCCESS(f"\n✓ Export complete!"))
        self.stdout.write(f"  Organizations: {orgs_dir}")
        self.stdout.write(f"  Users: {users_dir}")
        self.stdout.write(f"  Quests: {quest_dir}")
        self.stdout.write(f"  Media: {DEFAULT_MEDIA_DIR}")

    # --- Helper methods ---

    def _clear_demo_directories(self, quest_dir: str, users_dir: str, orgs_dir: str):
        """Clear existing demo directories."""
        # Clear quest directories (remove entire quest subdirectories)
        if os.path.exists(quest_dir):
            for item in os.listdir(quest_dir):
                item_path = os.path.join(quest_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    self.stdout.write(f"  Removed quest directory: {item}")

        # Clear user JSON files
        if os.path.exists(users_dir):
            for filename in os.listdir(users_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(users_dir, filename))
                    self.stdout.write(f"  Removed user: {filename}")

        # Clear organization JSON files
        if os.path.exists(orgs_dir):
            for filename in os.listdir(orgs_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(orgs_dir, filename))
                    self.stdout.write(f"  Removed organization: {filename}")

        # Clear media directory
        if os.path.exists(DEFAULT_MEDIA_DIR):
            for filename in os.listdir(DEFAULT_MEDIA_DIR):
                if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    os.remove(os.path.join(DEFAULT_MEDIA_DIR, filename))
                    self.stdout.write(f"  Removed media: {filename}")

    def _slugify_filename(self, text: str) -> str:
        """Convert text to a slug suitable for filenames."""
        # Convert to lowercase and replace spaces with hyphens
        text = text.lower().strip()
        # Remove special characters except hyphens and underscores
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text

    def _export_organizations(self, organizations: list, orgs_dir: str):
        """Export organizations to JSON files."""
        self.stdout.write(f"\nExporting {len(organizations)} organization(s)...")

        for org in organizations:
            org_data = {
                "slug": org.slug,
                "name": org.name,
                "description": org.description or "",
                "is_active": org.is_active,
                "meta": org.meta or {},
            }

            org_filename = f"{org.slug}.json"
            org_path = os.path.join(orgs_dir, org_filename)

            with open(org_path, 'w', encoding='utf-8') as f:
                json.dump(org_data, f, indent=2, ensure_ascii=False)

            self.stdout.write(f"  Exported organization: {org.slug}")

    def _export_users(self, users: Set[User], users_dir: str):
        """Export users with their organization roles and quest enrollments."""
        self.stdout.write(f"\nExporting {len(users)} user(s)...")

        for user in users:
            # Generate filename from email
            email_parts = user.email.split('@')[0]
            user_filename = f"{self._slugify_filename(email_parts)}.json"

            # Note: Passwords can't be exported from hashed values in DB
            # You may need to manually set the correct demo password after export
            user_data = {
                "email": user.email,
                "password": "demo123",  # NOTE: Update with actual demo password if needed
                "first_name": user.first_name,
                "last_name": user.last_name,
                "bio": user.bio or "",
                "tagline": user.tagline or "",
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "organization_roles": [],
                "quest_enrollments": [],
            }

            # Get organization roles
            org_admins = OrganizationAdmin.objects.filter(user=user).select_related('organization')
            for admin in org_admins:
                user_data["organization_roles"].append({
                    "organization_slug": admin.organization.slug,
                    "role": admin.role,
                })

            # Get quest enrollments
            enrollments = QuestEnrollment.objects.filter(user=user).select_related('quest_template')
            for enrollment in enrollments:
                user_data["quest_enrollments"].append({
                    "quest_title": enrollment.quest_template.title,
                    "status": enrollment.status,
                })

            user_path = os.path.join(users_dir, user_filename)
            with open(user_path, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)

            self.stdout.write(f"  Exported user: {user.email}")

    def _export_quests(self, quests: list, quest_dir: str):
        """Export quests with their activities to quest-specific subdirectories."""
        self.stdout.write(f"\nExporting {len(quests)} quest(s)...")

        for quest in quests:
            # Create quest directory (slugified quest title)
            quest_slug = self._slugify_filename(quest.title)
            quest_path = os.path.join(quest_dir, quest_slug)
            activities_path = os.path.join(quest_path, "activities")

            os.makedirs(quest_path, exist_ok=True)
            os.makedirs(activities_path, exist_ok=True)

            # Export quest config
            quest_data = self._export_quest_config(quest)
            config_path = os.path.join(quest_path, "config.json")

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(quest_data, f, indent=2, ensure_ascii=False)

            self.stdout.write(f"  Exported quest config: {quest_slug}/config.json")

            # Export activities for this quest
            activities_to_export = []
            for item in quest.template_items.all():
                if item.item_definition.item_type == 'activity' and item.item_definition.activity:
                    activities_to_export.append(item.item_definition.activity)

            self.stdout.write(f"    Exporting {len(activities_to_export)} activities for quest '{quest.title}'...")

            for activity in activities_to_export:
                activity_data = self._export_activity(activity, quest.organization)

                activity_filename = f"{activity.slug}.json"
                activity_path = os.path.join(activities_path, activity_filename)

                with open(activity_path, 'w', encoding='utf-8') as f:
                    json.dump(activity_data, f, indent=2, ensure_ascii=False)

                self.stdout.write(f"      Exported activity: {activity.slug}")

    def _export_quest_config(self, quest: QuestTemplate) -> Dict[str, Any]:
        """Export a quest template config to JSON format matching the import format."""
        quest_data = {
            "title": quest.title,
            "description": quest.description,
            "organization_slug": quest.organization.slug,
            "created_by_email": quest.created_by.email if quest.created_by else None,
            "color": quest.color or "#4CAF50",
            "category": quest.category or "Introduction",
            "status": quest.status,
            "is_public": quest.is_public,
            "is_template": quest.is_template,
            "meta": quest.meta or {},
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

    def _export_activity(self, activity: Activity, organization: Organization) -> Dict[str, Any]:
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
                "number": version.version,
                "title": version.title,
                "description": version.description,
                "meta": version.meta or {},
                "is_published": version.is_published,
            },
            "media_assets": [],
            "pages": []
        }

        # Process pages
        for page in version.pages.all().order_by('index'):
            page_data = {
                "index": page.index,
                "title": page.title or "",
                "meta": page.meta or {},
                "blocks": []
            }

            # Process blocks
            for block in page.blocks.all().order_by('index'):
                block_data = {
                    "index": block.index,
                    "block_type": block.block_type,
                    "config": dict(block.config) if block.config else {}
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
                        self.stdout.write(self.style.WARNING(f"        Media asset {media_id} not found"))

                page_data["blocks"].append(block_data)

            activity_data["pages"].append(page_data)

        # Add media assets section
        for filename, media in media_assets.items():
            activity_data["media_assets"].append({
                "filename": filename,
                "path": filename,  # Simplified path
                "title": media.meta.get('title', filename) if media.meta else filename,
                "description": media.meta.get('description', '') if media.meta else '',
                "alt_text": media.meta.get('alt_text', media.meta.get('description', '')) if media.meta else ''
            })

        return activity_data

    def _get_media_filename(self, media: MediaAsset) -> str:
        """Generate a simple filename for a media asset using its ID."""
        # Use extension from storage_key or mime_type
        ext = os.path.splitext(media.storage_key)[1] if media.storage_key else '.png'
        if not ext:
            # Fallback to extension from mime_type
            ext = '.png'
            if media.mime_type:
                if 'jpeg' in media.mime_type or 'jpg' in media.mime_type:
                    ext = '.jpg'
                elif 'gif' in media.mime_type:
                    ext = '.gif'
                elif 'webp' in media.mime_type:
                    ext = '.webp'
        return f"{media.id}{ext}"

    def _export_media_file(self, media: MediaAsset, filename: str) -> None:
        """Export a media file from storage to the demo/media directory."""
        from django.core.files.storage import default_storage

        media_dir = DEFAULT_MEDIA_DIR
        dest_path = os.path.join(media_dir, filename)

        # Skip if already exported
        if os.path.exists(dest_path):
            return

        try:
            # Read from storage
            if default_storage.exists(media.storage_key):
                with default_storage.open(media.storage_key, 'rb') as source_file:
                    file_content = source_file.read()

                # Write to demo/media directory
                with open(dest_path, 'wb') as dest_file:
                    dest_file.write(file_content)

                self.stdout.write(f"        Exported media: {filename}")
            else:
                self.stdout.write(self.style.WARNING(f"        Media file not found in storage: {media.storage_key}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"        Failed to export media {filename}: {e}"))
