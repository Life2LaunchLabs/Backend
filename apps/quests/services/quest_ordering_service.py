"""
Quest item ordering service - handles atomic reordering with database-level integrity.
"""
from django.db import transaction, models
from ..models import QuestTemplateItem


class QuestOrderingService:
    """
    Service for managing quest item ordering with atomic transactions.
    Ensures ordering integrity at the database level.
    """

    @staticmethod
    @transaction.atomic
    def reorder_items(quest_template_id, item_orders):
        """
        Atomically reorder quest items.

        Args:
            quest_template_id: UUID of the quest template
            item_orders: List of dicts with 'id' and 'order'
                Example: [
                    {'id': 'uuid-1', 'order': 0},
                    {'id': 'uuid-2', 'order': 1},
                    {'id': 'uuid-3', 'order': 2},
                ]

        Returns:
            List of updated QuestTemplateItem instances in order

        Raises:
            ValueError: If item id not found or order conflicts detected
        """
        # Lock items for update to prevent race conditions
        items = list(QuestTemplateItem.objects.select_for_update().filter(
            quest_template_id=quest_template_id
        ))

        if not items:
            raise ValueError(f"No items found for quest template {quest_template_id}")

        # Create order map (accept both 'id' and 'item_id' for compatibility)
        order_map = {str(item.get('id') or item.get('item_id')): item['order'] for item in item_orders}

        # Validate all items exist
        item_ids = {str(item.id) for item in items}
        provided_ids = set(order_map.keys())
        missing_ids = provided_ids - item_ids
        if missing_ids:
            raise ValueError(f"Items not found: {missing_ids}")

        # Update orders using two-phase approach to avoid unique constraint violations
        # Phase 1: Set all items to temporary high values (starting from 10000)
        # This avoids conflicts with the final order values
        TEMP_ORDER_OFFSET = 10000
        for idx, item in enumerate(items):
            item.order = TEMP_ORDER_OFFSET + idx

        if items:
            QuestTemplateItem.objects.bulk_update(items, ['order'])

        # Phase 2: Set items to their final order values
        items_to_update = []
        for item in items:
            item_id_str = str(item.id)
            if item_id_str in order_map:
                new_order = order_map[item_id_str]
                item.order = new_order
                items_to_update.append(item)

        # Bulk update with final values
        if items_to_update:
            QuestTemplateItem.objects.bulk_update(items_to_update, ['order'])

        # Return updated items in order
        return list(QuestTemplateItem.objects.filter(
            quest_template_id=quest_template_id
        ).order_by('order').select_related(
            'item_definition',
            'item_definition__activity',
            'item_definition__organization'
        ).prefetch_related('prerequisites'))

    @staticmethod
    def get_next_order(quest_template_id):
        """
        Get the next available order number for a quest.

        Args:
            quest_template_id: UUID of quest template

        Returns:
            int: Next available order number (0-indexed)
        """
        max_order = QuestTemplateItem.objects.filter(
            quest_template_id=quest_template_id
        ).aggregate(models.Max('order'))['order__max']

        return (max_order + 1) if max_order is not None else 0

    @staticmethod
    @transaction.atomic
    def insert_item_at_position(quest_template_id, item_definition_id, position, **kwargs):
        """
        Insert a new item at a specific position, shifting others down.

        Args:
            quest_template_id: UUID of quest template
            item_definition_id: UUID of item definition to add
            position: Desired order position (0-indexed)
            **kwargs: Additional fields (override_duration_days, notes, etc.)

        Returns:
            QuestTemplateItem: Newly created item

        Raises:
            ValueError: If position is invalid or item already exists
        """
        from ..models import QuestItemDefinition

        # Validate item definition exists
        try:
            item_definition = QuestItemDefinition.objects.get(id=item_definition_id)
        except QuestItemDefinition.DoesNotExist:
            raise ValueError(f"Item definition {item_definition_id} not found")

        # Check if item already exists in quest
        existing = QuestTemplateItem.objects.filter(
            quest_template_id=quest_template_id,
            item_definition_id=item_definition_id
        ).exists()
        if existing:
            raise ValueError(f"Item {item_definition.title} already exists in this quest")

        # Lock and shift existing items at or after position
        items_to_shift = list(QuestTemplateItem.objects.select_for_update().filter(
            quest_template_id=quest_template_id,
            order__gte=position
        ).order_by('-order'))  # Process in reverse to avoid conflicts

        # Shift items
        for item in items_to_shift:
            item.order += 1

        if items_to_shift:
            QuestTemplateItem.objects.bulk_update(items_to_shift, ['order'])

        # Create new item at position
        new_item = QuestTemplateItem.objects.create(
            quest_template_id=quest_template_id,
            item_definition_id=item_definition_id,
            order=position,
            **kwargs
        )

        return new_item

    @staticmethod
    @transaction.atomic
    def append_item(quest_template_id, item_definition_id, **kwargs):
        """
        Append a new item to the end of the quest.

        Args:
            quest_template_id: UUID of quest template
            item_definition_id: UUID of item definition to add
            **kwargs: Additional fields (override_duration_days, notes, etc.)

        Returns:
            QuestTemplateItem: Newly created item

        Raises:
            ValueError: If item definition not found or already exists
        """
        from ..models import QuestItemDefinition

        # Validate item definition exists
        try:
            item_definition = QuestItemDefinition.objects.get(id=item_definition_id)
        except QuestItemDefinition.DoesNotExist:
            raise ValueError(f"Item definition {item_definition_id} not found")

        # Check if item already exists in quest
        existing = QuestTemplateItem.objects.filter(
            quest_template_id=quest_template_id,
            item_definition_id=item_definition_id
        ).exists()
        if existing:
            raise ValueError(f"Item {item_definition.title} already exists in this quest")

        # Get next order number
        next_order = QuestOrderingService.get_next_order(quest_template_id)

        # Create new item
        new_item = QuestTemplateItem.objects.create(
            quest_template_id=quest_template_id,
            item_definition_id=item_definition_id,
            order=next_order,
            **kwargs
        )

        return new_item

    @staticmethod
    @transaction.atomic
    def remove_item(quest_template_id, template_item_id):
        """
        Remove an item from the quest and reorder remaining items.

        Args:
            quest_template_id: UUID of quest template
            template_item_id: UUID of QuestTemplateItem to remove

        Returns:
            bool: True if item was removed

        Raises:
            ValueError: If item not found
        """
        try:
            item = QuestTemplateItem.objects.select_for_update().get(
                id=template_item_id,
                quest_template_id=quest_template_id
            )
        except QuestTemplateItem.DoesNotExist:
            raise ValueError(f"Item {template_item_id} not found in quest {quest_template_id}")

        removed_order = item.order

        # Delete the item
        item.delete()

        # Shift items after the removed one
        items_to_shift = list(QuestTemplateItem.objects.select_for_update().filter(
            quest_template_id=quest_template_id,
            order__gt=removed_order
        ).order_by('order'))

        for item in items_to_shift:
            item.order -= 1

        if items_to_shift:
            QuestTemplateItem.objects.bulk_update(items_to_shift, ['order'])

        return True

    @staticmethod
    def validate_prerequisite_cycles(quest_template_id):
        """
        Validate that there are no circular dependencies in prerequisites.

        Args:
            quest_template_id: UUID of quest template

        Returns:
            tuple: (is_valid, error_message)
                   is_valid=True if no cycles found
                   error_message describes the cycle if found

        This uses depth-first search to detect cycles.
        """
        items = QuestTemplateItem.objects.filter(
            quest_template_id=quest_template_id
        ).prefetch_related('prerequisites')

        # Build adjacency list
        adjacency = {}
        for item in items:
            adjacency[item.id] = [prereq.id for prereq in item.prerequisites.all()]

        # DFS to detect cycles
        visited = set()
        recursion_stack = set()

        def has_cycle(item_id, path):
            visited.add(item_id)
            recursion_stack.add(item_id)

            for prereq_id in adjacency.get(item_id, []):
                if prereq_id not in visited:
                    if has_cycle(prereq_id, path + [item_id]):
                        return True
                elif prereq_id in recursion_stack:
                    # Cycle detected
                    cycle_path = path + [item_id, prereq_id]
                    return True

            recursion_stack.remove(item_id)
            return False

        for item_id in adjacency.keys():
            if item_id not in visited:
                if has_cycle(item_id, []):
                    return False, "Circular prerequisite dependency detected"

        return True, None