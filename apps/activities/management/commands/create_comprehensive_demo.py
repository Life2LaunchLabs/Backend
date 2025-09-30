import os
import uuid
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.quests.models import Activity, ActivityVersion, Page, Block, MediaAsset
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = 'Create all demo activities and assessments'

    def handle(self, *args, **options):
        self.stdout.write('Creating all demo activities...')

        # Get Life2Launch organization
        try:
            life2launch_org = Organization.objects.get(slug='life2launch')
            self.stdout.write(f'Found Life2Launch organization: {life2launch_org.name}')
        except Organization.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Life2Launch organization not found. Please run create_default_admin_user first.')
            )
            return

        # Create media assets for our organized images
        media_assets = self.create_media_assets()

        # Create all demo activities
        activities = []

        # 1. Comprehensive mindfulness journey (original)
        activity1 = self.create_comprehensive_activity(media_assets, life2launch_org)
        activities.append(activity1)

        # 2. Simple mindful morning (original demo)
        activity2 = self.create_mindful_morning_activity(life2launch_org)
        activities.append(activity2)

        # 3. New: Career exploration assessment
        activity3 = self.create_career_exploration_activity(life2launch_org)
        activities.append(activity3)

        # 4. New: Personal values discovery
        activity4 = self.create_values_discovery_activity(life2launch_org)
        activities.append(activity4)

        # 5. New: Goal setting workshop
        activity5 = self.create_goal_setting_activity(life2launch_org)
        activities.append(activity5)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(activities)} demo activities: '
                f'{", ".join([a.slug for a in activities])}'
            )
        )

    def create_media_assets(self):
        """Create MediaAsset records for our organized demo images."""
        media_data = [
            {
                'filename': 'peaceful_environment.png',
                'path': 'activity_media/illustrations/peaceful_environment.png',
                'title': 'Peaceful Environment',
                'description': 'A calming, serene environment for reflection'
            },
            {
                'filename': 'reflection_example.png',
                'path': 'activity_media/examples/reflection_example.png',
                'title': 'Reflection Journal',
                'description': 'Example of personal reflection and journaling'
            },
            {
                'filename': 'discovery_concept.png',
                'path': 'activity_media/illustrations/discovery_concept.png',
                'title': 'Discovery and Learning',
                'description': 'Illustration representing discovery and exploration'
            },
            {
                'filename': 'choice_scenario.png',
                'path': 'activity_media/examples/choice_scenario.png',
                'title': 'Decision Making Scenario',
                'description': 'Visual example of making choices and decisions'
            },
            {
                'filename': 'progress_visualization.png',
                'path': 'activity_media/interface_demos/progress_visualization.png',
                'title': 'Progress and Growth',
                'description': 'Visualization of learning progress and skill development'
            },
            {
                'filename': 'future_concept.png',
                'path': 'activity_media/examples/future_concept.png',
                'title': 'Future Possibilities',
                'description': 'Conceptual image representing future opportunities'
            }
        ]

        created_assets = {}
        for data in media_data:
            # Check if file exists
            full_path = os.path.join(settings.MEDIA_ROOT, data['path'])
            if os.path.exists(full_path):
                # Create or get existing MediaAsset
                asset, created = MediaAsset.objects.get_or_create(
                    storage_key=data['path'],
                    defaults={
                        'mime_type': 'image/png',
                        'meta': {
                            'title': data['title'],
                            'description': data['description'],
                            'alt_text': data['description']
                        }
                    }
                )
                created_assets[data['filename']] = asset
                if created:
                    self.stdout.write(f'Created MediaAsset: {data["title"]}')
                else:
                    self.stdout.write(f'Found existing MediaAsset: {data["title"]}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'File not found: {full_path}')
                )

        return created_assets

    def create_comprehensive_activity(self, media_assets, organization):
        """Create a comprehensive demo activity showcasing all block types."""

        # Create or get the activity
        activity, created = Activity.objects.get_or_create(
            slug='comprehensive-mindfulness-journey',
            defaults={
                'status': 'published',
                'organization': organization
            }
        )

        if not created:
            # Delete existing version to recreate
            activity.versions.all().delete()

        # Create new version
        version = ActivityVersion.objects.create(
            activity=activity,
            version=1,
            title='Comprehensive Mindfulness Journey - Full Demo',
            description='Experience the complete range of Activities features including media blocks, diverse question types, and interactive content.',
            meta={
                'estimated_duration': '15-20 minutes',
                'difficulty': 'beginner_to_intermediate',
                'topics': ['mindfulness', 'self-reflection', 'decision-making', 'goal-setting']
            },
            is_published=True
        )

        # Create pages with comprehensive content
        self.create_introduction_page(version, media_assets)
        self.create_reflection_page(version, media_assets)
        self.create_assessment_page(version, media_assets)
        self.create_planning_page(version, media_assets)
        self.create_conclusion_page(version, media_assets)

        return activity

    def create_introduction_page(self, version, media_assets):
        """Page 0: Introduction with media and welcome content."""
        page = Page.objects.create(
            activity_version=version,
            index=0,
            title='Welcome to Your Mindfulness Journey',
            meta={'page_type': 'introduction'}
        )

        # Welcome text block
        Block.objects.create(
            page=page,
            index=0,
            block_type='text',
            config={
                'style': 'h1',
                'content': 'Welcome to Your Mindfulness Journey'
            }
        )

        # Hero image
        if 'peaceful_environment.png' in media_assets:
            Block.objects.create(
                page=page,
                index=1,
                block_type='media',
                config={
                    'media_id': str(media_assets['peaceful_environment.png'].id),
                    'caption': 'Take a moment to center yourself as we begin this journey together.',
                    'size': 'large'
                }
            )

        # Introduction text
        Block.objects.create(
            page=page,
            index=2,
            block_type='text',
            config={
                'style': 'body',
                'content': 'This comprehensive assessment will guide you through various aspects of mindfulness and self-reflection. You\'ll encounter different types of questions, interactive elements, and visual content designed to help you explore your thoughts, feelings, and goals.'
            }
        )

        # Getting started text
        Block.objects.create(
            page=page,
            index=3,
            block_type='text',
            config={
                'style': 'lead',
                'content': 'Take your time with each section. There are no right or wrong answers—this is about your personal journey and insights.'
            }
        )

    def create_reflection_page(self, version, media_assets):
        """Page 1: Personal reflection with various question types."""
        page = Page.objects.create(
            activity_version=version,
            index=1,
            title='Personal Reflection',
            meta={'page_type': 'reflection'}
        )

        # Page title
        Block.objects.create(
            page=page,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'content': 'Personal Reflection & Self-Awareness'
            }
        )

        # Reflection image
        if 'reflection_example.png' in media_assets:
            Block.objects.create(
                page=page,
                index=1,
                block_type='media',
                config={
                    'media_id': str(media_assets['reflection_example.png'].id),
                    'caption': 'Reflection is the foundation of mindful living.',
                    'size': 'medium'
                }
            )

        # Text input question
        Block.objects.create(
            page=page,
            index=2,
            block_type='question',
            config={
                'question_id': 'current_mood',
                'question_type': 'text_input',
                'question_text': 'How would you describe your current emotional state in a few words?',
                'placeholder': 'Take a moment to check in with yourself...',
                'required': True
            }
        )

        # Multiple choice question
        Block.objects.create(
            page=page,
            index=3,
            block_type='question',
            config={
                'question_id': 'mindfulness_frequency',
                'question_type': 'multiple_choice',
                'question_text': 'How often do you practice mindfulness or meditation?',
                'options': [
                    {'value': 'daily', 'label': 'Daily'},
                    {'value': 'weekly', 'label': 'Several times a week'},
                    {'value': 'monthly', 'label': 'A few times a month'},
                    {'value': 'rarely', 'label': 'Rarely or never'},
                    {'value': 'just_starting', 'label': 'I\'m just starting to explore it'}
                ],
                'required': True
            }
        )

        # Long form reflection
        Block.objects.create(
            page=page,
            index=4,
            block_type='question',
            config={
                'question_id': 'gratitude_reflection',
                'question_type': 'text_input',
                'question_text': 'What are three things you\'re grateful for today? Take a moment to really consider why each one matters to you.',
                'placeholder': '1. ...\n2. ...\n3. ...',
                'multiline': True,
                'required': False
            }
        )

    def create_assessment_page(self, version, media_assets):
        """Page 2: Assessment with choice scenarios."""
        page = Page.objects.create(
            activity_version=version,
            index=2,
            title='Mindful Decision Making',
            meta={'page_type': 'assessment'}
        )

        # Page title
        Block.objects.create(
            page=page,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'content': 'Mindful Decision Making'
            }
        )

        # Discovery image
        if 'discovery_concept.png' in media_assets:
            Block.objects.create(
                page=page,
                index=1,
                block_type='media',
                config={
                    'media_id': str(media_assets['discovery_concept.png'].id),
                    'caption': 'Every choice is an opportunity for growth and discovery.',
                    'size': 'medium'
                }
            )

        # Scenario introduction
        Block.objects.create(
            page=page,
            index=2,
            block_type='text',
            config={
                'style': 'body',
                'content': 'Consider the following scenarios and reflect on how mindfulness might guide your choices.'
            }
        )

        # Scenario-based question
        Block.objects.create(
            page=page,
            index=3,
            block_type='question',
            config={
                'question_id': 'stress_response',
                'question_type': 'single_choice',
                'question_text': 'You\'re facing a stressful deadline at work. Which approach feels most aligned with mindful living?',
                'options': [
                    {'value': 'rush_panic', 'label': 'Rush through tasks, accepting stress as inevitable'},
                    {'value': 'pause_breathe', 'label': 'Pause, take three deep breaths, then prioritize mindfully'},
                    {'value': 'avoid_procrastinate', 'label': 'Avoid the stress by procrastinating or distraction'},
                    {'value': 'push_through', 'label': 'Push through with determination, ignoring physical/emotional signals'}
                ],
                'required': True
            }
        )

        # Choice scenario image
        if 'choice_scenario.png' in media_assets:
            Block.objects.create(
                page=page,
                index=4,
                block_type='media',
                config={
                    'media_id': str(media_assets['choice_scenario.png'].id),
                    'caption': 'Mindful choices create ripple effects in our lives.',
                    'size': 'small'
                }
            )

        # Values assessment
        Block.objects.create(
            page=page,
            index=5,
            block_type='question',
            config={
                'question_id': 'core_values',
                'question_type': 'multiple_choice',
                'question_text': 'Which values are most important to you in daily life? (Select all that apply)',
                'options': [
                    {'value': 'compassion', 'label': 'Compassion and kindness'},
                    {'value': 'authenticity', 'label': 'Authenticity and honesty'},
                    {'value': 'growth', 'label': 'Personal growth and learning'},
                    {'value': 'connection', 'label': 'Connection and relationships'},
                    {'value': 'peace', 'label': 'Inner peace and calm'},
                    {'value': 'purpose', 'label': 'Sense of purpose and meaning'},
                    {'value': 'balance', 'label': 'Work-life balance'},
                    {'value': 'creativity', 'label': 'Creativity and expression'}
                ],
                'required': False,
                'multiple_selection': True
            }
        )

    def create_planning_page(self, version, media_assets):
        """Page 3: Goal setting and future planning."""
        page = Page.objects.create(
            activity_version=version,
            index=3,
            title='Mindful Goal Setting',
            meta={'page_type': 'planning'}
        )

        # Page title
        Block.objects.create(
            page=page,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'content': 'Mindful Goal Setting & Intentions'
            }
        )

        # Progress visualization
        if 'progress_visualization.png' in media_assets:
            Block.objects.create(
                page=page,
                index=1,
                block_type='media',
                config={
                    'media_id': str(media_assets['progress_visualization.png'].id),
                    'caption': 'Growth happens step by step, with mindful intention.',
                    'size': 'large'
                }
            )

        # Goal setting introduction
        Block.objects.create(
            page=page,
            index=2,
            block_type='text',
            config={
                'style': 'body',
                'content': 'Mindful goal setting involves setting intentions that align with your values and current capacity for growth.'
            }
        )

        # Intention setting
        Block.objects.create(
            page=page,
            index=3,
            block_type='question',
            config={
                'question_id': 'mindfulness_intention',
                'question_type': 'text_input',
                'question_text': 'What is one mindfulness practice or habit you\'d like to cultivate over the next month?',
                'placeholder': 'Be specific and realistic...',
                'required': True
            }
        )

        # Support system question
        Block.objects.create(
            page=page,
            index=4,
            block_type='question',
            config={
                'question_id': 'support_preference',
                'question_type': 'single_choice',
                'question_text': 'How do you prefer to stay accountable to your mindfulness goals?',
                'options': [
                    {'value': 'self_reflection', 'label': 'Regular self-reflection and journaling'},
                    {'value': 'accountability_partner', 'label': 'An accountability partner or friend'},
                    {'value': 'structured_program', 'label': 'A structured program or course'},
                    {'value': 'community_group', 'label': 'A mindfulness community or group'},
                    {'value': 'apps_reminders', 'label': 'Apps, reminders, or digital tools'},
                    {'value': 'flexible_approach', 'label': 'I prefer a flexible, intuitive approach'}
                ],
                'required': True
            }
        )

        # Obstacles anticipation
        Block.objects.create(
            page=page,
            index=5,
            block_type='question',
            config={
                'question_id': 'anticipated_challenges',
                'question_type': 'text_input',
                'question_text': 'What challenges do you anticipate in maintaining your mindfulness practice? How might you work with them compassionately?',
                'placeholder': 'Consider both external obstacles and internal resistance...',
                'multiline': True,
                'required': False
            }
        )

    def create_conclusion_page(self, version, media_assets):
        """Page 4: Conclusion and next steps."""
        page = Page.objects.create(
            activity_version=version,
            index=4,
            title='Your Path Forward',
            meta={'page_type': 'conclusion'}
        )

        # Page title
        Block.objects.create(
            page=page,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'content': 'Your Mindful Path Forward'
            }
        )

        # Future possibilities image
        if 'future_concept.png' in media_assets:
            Block.objects.create(
                page=page,
                index=1,
                block_type='media',
                config={
                    'media_id': str(media_assets['future_concept.png'].id),
                    'caption': 'Every moment offers a fresh opportunity for mindful awareness.',
                    'size': 'medium'
                }
            )

        # Completion reflection
        Block.objects.create(
            page=page,
            index=2,
            block_type='text',
            config={
                'style': 'body',
                'content': 'Thank you for taking this journey of self-reflection and mindful exploration. The insights you\'ve gained here are just the beginning.'
            }
        )

        # Key takeaways
        Block.objects.create(
            page=page,
            index=3,
            block_type='text',
            config={
                'style': 'quote',
                'content': 'Remember: Mindfulness is not about perfection—it\'s about presence, compassion, and gentle awareness of each moment as it unfolds.'
            }
        )

        # Final reflection question
        Block.objects.create(
            page=page,
            index=4,
            block_type='question',
            config={
                'question_id': 'closing_reflection',
                'question_type': 'text_input',
                'question_text': 'As we conclude, what is one word or phrase that captures how you\'re feeling right now?',
                'placeholder': 'Trust your first instinct...',
                'required': False
            }
        )

        # Encouraging closing
        Block.objects.create(
            page=page,
            index=5,
            block_type='text',
            config={
                'style': 'lead',
                'content': 'May you carry the spirit of mindful awareness with you in all that you do. Your journey continues with each conscious breath and intentional choice.'
            }
        )

    def create_mindful_morning_activity(self, organization):
        """Create a simple mindful morning activity."""

        # Create or get the activity
        activity, created = Activity.objects.get_or_create(
            slug='demo-mindful-morning',
            defaults={
                'status': 'published',
                'organization': organization
            }
        )

        if not created:
            # Delete existing version to recreate
            activity.versions.all().delete()

        # Create new version
        version = ActivityVersion.objects.create(
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
            activity_version=version,
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
                'content': 'Welcome to Your Mindful Morning'
            }
        )

        Block.objects.create(
            page=page1,
            index=1,
            block_type='text',
            config={
                'style': 'body',
                'content': 'Take a moment to center yourself and begin this journey of mindfulness.'
            }
        )

        # Page 2: Reflection questions
        page2 = Page.objects.create(
            activity_version=version,
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
                'content': 'How are you feeling this morning?'
            }
        )

        Block.objects.create(
            page=page2,
            index=1,
            block_type='question',
            config={
                'question_id': 'morning_feeling',
                'question_type': 'multiple_choice',
                'question_text': 'Select all that apply:',
                'required': True,
                'options': [
                    {'value': 'calm', 'label': 'Calm'},
                    {'value': 'energized', 'label': 'Energized'},
                    {'value': 'anxious', 'label': 'Anxious'},
                    {'value': 'tired', 'label': 'Tired'}
                ]
            }
        )

        return activity

    def create_career_exploration_activity(self, organization):
        """Create a career exploration assessment."""

        activity, created = Activity.objects.get_or_create(
            slug='career-exploration-assessment',
            defaults={
                'status': 'published',
                'organization': organization
            }
        )

        if not created:
            activity.versions.all().delete()

        version = ActivityVersion.objects.create(
            activity=activity,
            version=1,
            title='Career Exploration Assessment',
            description='Discover your career interests and strengths',
            is_published=True,
            meta={'demo': True, 'category': 'career'}
        )

        # Introduction page
        page1 = Page.objects.create(
            activity_version=version,
            index=0,
            title='Career Discovery',
            meta={'progress_label': 'Introduction'}
        )

        Block.objects.create(
            page=page1,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'content': 'Explore Your Career Path'
            }
        )

        Block.objects.create(
            page=page1,
            index=1,
            block_type='text',
            config={
                'style': 'body',
                'content': 'This assessment will help you discover career paths that align with your interests and strengths.'
            }
        )

        # Assessment page
        page2 = Page.objects.create(
            activity_version=version,
            index=1,
            title='Career Interests',
            meta={'progress_label': 'Assessment'}
        )

        Block.objects.create(
            page=page2,
            index=0,
            block_type='question',
            config={
                'question_id': 'work_environment',
                'question_type': 'single_choice',
                'question_text': 'What type of work environment appeals to you most?',
                'options': [
                    {'value': 'collaborative', 'label': 'Collaborative team environment'},
                    {'value': 'independent', 'label': 'Independent, self-directed work'},
                    {'value': 'client_facing', 'label': 'Client-facing and relationship-building'},
                    {'value': 'creative', 'label': 'Creative and innovative projects'}
                ],
                'required': True
            }
        )

        Block.objects.create(
            page=page2,
            index=1,
            block_type='question',
            config={
                'question_id': 'career_goals',
                'question_type': 'text_input',
                'question_text': 'Describe your ideal career in one sentence.',
                'placeholder': 'My ideal career would be...',
                'multiline': True,
                'required': False
            }
        )

        return activity

    def create_values_discovery_activity(self, organization):
        """Create a personal values discovery activity."""

        activity, created = Activity.objects.get_or_create(
            slug='personal-values-discovery',
            defaults={
                'status': 'published',
                'organization': organization
            }
        )

        if not created:
            activity.versions.all().delete()

        version = ActivityVersion.objects.create(
            activity=activity,
            version=1,
            title='Personal Values Discovery',
            description='Identify and prioritize your core personal values',
            is_published=True,
            meta={'demo': True, 'category': 'values'}
        )

        # Introduction page
        page1 = Page.objects.create(
            activity_version=version,
            index=0,
            title='Values Exploration',
            meta={'progress_label': 'Introduction'}
        )

        Block.objects.create(
            page=page1,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'content': 'Discover Your Core Values'
            }
        )

        Block.objects.create(
            page=page1,
            index=1,
            block_type='text',
            config={
                'style': 'body',
                'content': 'Understanding your personal values helps guide important life decisions and creates a foundation for authentic living.'
            }
        )

        # Values selection page
        page2 = Page.objects.create(
            activity_version=version,
            index=1,
            title='Value Priorities',
            meta={'progress_label': 'Selection'}
        )

        Block.objects.create(
            page=page2,
            index=0,
            block_type='question',
            config={
                'question_id': 'top_values',
                'question_type': 'multiple_choice',
                'question_text': 'Select your top 5 most important values:',
                'options': [
                    {'value': 'authenticity', 'label': 'Authenticity'},
                    {'value': 'creativity', 'label': 'Creativity'},
                    {'value': 'family', 'label': 'Family'},
                    {'value': 'growth', 'label': 'Personal Growth'},
                    {'value': 'integrity', 'label': 'Integrity'},
                    {'value': 'freedom', 'label': 'Freedom'},
                    {'value': 'service', 'label': 'Service to Others'},
                    {'value': 'achievement', 'label': 'Achievement'},
                    {'value': 'balance', 'label': 'Work-Life Balance'},
                    {'value': 'adventure', 'label': 'Adventure'}
                ],
                'required': True,
                'multiple_selection': True
            }
        )

        return activity

    def create_goal_setting_activity(self, organization):
        """Create a goal setting workshop activity."""

        activity, created = Activity.objects.get_or_create(
            slug='goal-setting-workshop',
            defaults={
                'status': 'published',
                'organization': organization
            }
        )

        if not created:
            activity.versions.all().delete()

        version = ActivityVersion.objects.create(
            activity=activity,
            version=1,
            title='Goal Setting Workshop',
            description='Learn to set and achieve meaningful personal goals',
            is_published=True,
            meta={'demo': True, 'category': 'goals'}
        )

        # Introduction page
        page1 = Page.objects.create(
            activity_version=version,
            index=0,
            title='Goal Setting Basics',
            meta={'progress_label': 'Introduction'}
        )

        Block.objects.create(
            page=page1,
            index=0,
            block_type='text',
            config={
                'style': 'h2',
                'content': 'Setting Meaningful Goals'
            }
        )

        Block.objects.create(
            page=page1,
            index=1,
            block_type='text',
            config={
                'style': 'body',
                'content': 'Effective goal setting combines clarity, motivation, and practical planning to help you achieve what matters most.'
            }
        )

        # Goal planning page
        page2 = Page.objects.create(
            activity_version=version,
            index=1,
            title='Your Goals',
            meta={'progress_label': 'Planning'}
        )

        Block.objects.create(
            page=page2,
            index=0,
            block_type='question',
            config={
                'question_id': 'primary_goal',
                'question_type': 'text_input',
                'question_text': 'What is one important goal you want to achieve in the next 6 months?',
                'placeholder': 'Be specific and actionable...',
                'multiline': True,
                'required': True
            }
        )

        Block.objects.create(
            page=page2,
            index=1,
            block_type='question',
            config={
                'question_id': 'goal_motivation',
                'question_type': 'single_choice',
                'question_text': 'What is your primary motivation for this goal?',
                'options': [
                    {'value': 'personal_growth', 'label': 'Personal growth and development'},
                    {'value': 'career_advancement', 'label': 'Career advancement'},
                    {'value': 'relationships', 'label': 'Improving relationships'},
                    {'value': 'health_wellness', 'label': 'Health and wellness'},
                    {'value': 'financial', 'label': 'Financial security'},
                    {'value': 'creative_expression', 'label': 'Creative expression'}
                ],
                'required': True
            }
        )

        return activity