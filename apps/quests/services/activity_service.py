from ..models import Activity, ActivityVersion, Page, Block


class ActivityService:
    """Service for activity-related operations."""

    @staticmethod
    def create_demo_activity() -> Activity:
        """Create a demo activity with sample content for testing."""

        # Create activity (only non-version-specific fields)
        activity = Activity.objects.create(
            slug='demo-mindful-morning',
            status='draft',
            author_meta={'created_by': 'system', 'demo': True}
        )

        # Create activity version (with title and description)
        activity_version = ActivityVersion.objects.create(
            activity=activity,
            version=1,
            title='Demo: Mindful Morning',
            description='A sample activity showcasing different block types',
            is_published=True,
            meta={'demo': True}
        )

        # Create pages with blocks
        # Page 1: Welcome page
        page1 = Page.objects.create(
            activity_version=activity_version,
            index=0,
            title='Welcome',
            meta={'progress_label': 'Introduction'}
        )

        Block.objects.create(
            page=page1,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'text': 'Welcome to Your Mindful Morning',
                'align': 'center'
            }
        )

        Block.objects.create(
            page=page1,
            index=1,
            block_type='text',
            config={
                'style': 'body',
                'text': 'Take a moment to center yourself and begin this journey of mindfulness.',
                'align': 'center'
            }
        )

        # Page 2: Reflection questions
        page2 = Page.objects.create(
            activity_version=activity_version,
            index=1,
            title='Morning Reflection',
            meta={'progress_label': 'Reflection'}
        )

        Block.objects.create(
            page=page2,
            index=0,
            block_type='text',
            config={
                'style': 'h3',
                'text': 'How are you feeling this morning?',
                'align': 'left'
            }
        )

        Block.objects.create(
            page=page2,
            index=1,
            block_type='question',
            config={
                'question_id': 'morning_feeling',
                'question_type': 'multiple_choice',
                'title': 'Select all that apply:',
                'required': True,
                'config': {
                    'min_select': 1,
                    'max_select': 3,
                    'options': [
                        {'id': 'calm', 'title': 'Calm', 'body': 'Feeling peaceful and centered'},
                        {'id': 'energized', 'title': 'Energized', 'body': 'Ready to take on the day'},
                        {'id': 'anxious', 'title': 'Anxious', 'body': 'Feeling worried or nervous'},
                        {'id': 'tired', 'title': 'Tired', 'body': 'Still feeling sleepy or low energy'}
                    ]
                }
            }
        )

        Block.objects.create(
            page=page2,
            index=2,
            block_type='question',
            config={
                'question_id': 'morning_intention',
                'question_type': 'text_input',
                'title': 'What is your intention for today?',
                'subtitle': 'Share what you hope to accomplish or how you want to feel',
                'required': False,
                'config': {
                    'placeholder': 'I intend to...',
                    'max_length': 500,
                    'multiline': True
                }
            }
        )

        # Page 3: Completion
        page3 = Page.objects.create(
            activity_version=activity_version,
            index=2,
            title='Complete',
            meta={'progress_label': 'Complete'}
        )

        Block.objects.create(
            page=page3,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'text': 'Well done!',
                'align': 'center'
            }
        )

        Block.objects.create(
            page=page3,
            index=1,
            block_type='text',
            config={
                'style': 'body',
                'text': 'You have completed this mindful morning activity. Take a moment to appreciate this time you\'ve given yourself.',
                'align': 'center'
            }
        )

        return activity
