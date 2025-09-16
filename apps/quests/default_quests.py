"""
Default quest data for new user initialization.
This module contains the default quests and milestones that are created
when a new user account is initialized in development mode.
"""
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Quest, Milestone

User = get_user_model()


def get_summer_job_quest_data():
    """
    Returns the summer job quest data structure.
    This quest is personal (created by the user themselves).
    """
    today = date.today()

    return {
        'title': 'Land a Summer Job',
        'description': 'A comprehensive quest to help you secure a meaningful summer internship or job opportunity. This quest will guide you through all the essential steps from self-assessment to landing the role.',
        'color': '#4CAF50',  # Green
        'milestones': [
            {
                'title': 'Complete Self-Assessment',
                'description': 'Identify your interests, strengths, skills, and career goals. Use career assessment tools and reflect on what type of summer role would be most valuable for your development.',
                'finish_date': today + timedelta(days=7),
                'order': 1,
            },
            {
                'title': 'Research Target Industries & Roles',
                'description': 'Research 3-5 industries and specific job roles that align with your interests and goals. Create a list of companies you\'d like to work for.',
                'finish_date': today + timedelta(days=14),
                'order': 2,
            },
            {
                'title': 'Update Resume & Portfolio',
                'description': 'Create or update your resume to highlight relevant experiences, skills, and achievements. If applicable, build or update your portfolio with relevant projects.',
                'finish_date': today + timedelta(days=21),
                'order': 3,
            },
            {
                'title': 'Craft Cover Letter Templates',
                'description': 'Write 2-3 cover letter templates that you can customize for different types of roles and industries you\'re targeting.',
                'finish_date': today + timedelta(days=28),
                'order': 4,
            },
            {
                'title': 'Network & Seek Referrals',
                'description': 'Reach out to your network (family, friends, professors, alumni) to let them know you\'re looking for summer opportunities. Ask for introductions and advice.',
                'finish_date': today + timedelta(days=35),
                'order': 5,
            },
            {
                'title': 'Apply to Target Positions',
                'description': 'Apply to 10-15 summer positions that match your criteria. Track your applications in a spreadsheet with company names, positions, and application dates.',
                'finish_date': today + timedelta(days=49),
                'order': 6,
            },
            {
                'title': 'Prepare for Interviews',
                'description': 'Practice common interview questions, research the companies you\'ve applied to, and prepare thoughtful questions to ask interviewers.',
                'finish_date': today + timedelta(days=56),
                'order': 7,
            },
            {
                'title': 'Complete Interview Process',
                'description': 'Attend interviews, send thank-you notes, and follow up appropriately with potential employers.',
                'finish_date': today + timedelta(days=70),
                'order': 8,
            },
            {
                'title': 'Evaluate & Accept Offer',
                'description': 'Review job offers, negotiate if appropriate, and make your final decision. Confirm start date and any pre-employment requirements.',
                'finish_date': today + timedelta(days=84),
                'order': 9,
            }
        ]
    }


def get_getting_started_quest_data():
    """
    Returns the getting started quest data structure.
    This quest is shared (created by life2launch organization).
    """
    today = date.today()

    return {
        'title': 'Getting Started: Discover Your Path',
        'description': 'Welcome to Life2Launch! This foundational quest will help you explore your values, strengths, and goals as you begin your journey toward meaningful career and life choices.',
        'color': '#2196F3',  # Blue
        'milestones': [
            {
                'title': 'Complete Your Profile',
                'description': 'Fill out your Life2Launch profile with basic information about yourself, your interests, and your current stage in life.',
                'finish_date': today + timedelta(days=3),
                'order': 1,
            },
            {
                'title': 'Values Assessment',
                'description': 'Complete the values assessment to identify what matters most to you in work and life. Understanding your core values will guide your decision-making.',
                'finish_date': today + timedelta(days=10),
                'order': 2,
            },
            {
                'title': 'Strengths Discovery',
                'description': 'Take the strengths assessment to identify your natural talents and abilities. Learn how to leverage these strengths in your career planning.',
                'finish_date': today + timedelta(days=17),
                'order': 3,
            },
            {
                'title': 'Goal Setting Workshop',
                'description': 'Learn the fundamentals of effective goal setting using the SMART criteria. Set 3 short-term and 2 long-term goals for yourself.',
                'finish_date': today + timedelta(days=24),
                'order': 4,
            },
            {
                'title': 'Create Your Vision Board',
                'description': 'Combine your values, strengths, and goals to create a personal vision board that represents your ideal future.',
                'finish_date': today + timedelta(days=31),
                'order': 5,
            },
            {
                'title': 'Connect with Mentors',
                'description': 'Explore the mentor network and connect with 1-2 mentors who align with your interests and goals.',
                'finish_date': today + timedelta(days=38),
                'order': 6,
            },
            {
                'title': 'Plan Your Next Steps',
                'description': 'Based on your self-discovery, create an action plan for the next 3 months. Identify specific quests and activities you want to pursue.',
                'finish_date': today + timedelta(days=45),
                'order': 7,
            }
        ]
    }


def get_or_create_life2launch_user():
    """
    Get or create the life2launch organization user.
    This user represents the organization that creates shared quests.
    """
    life2launch_user, created = User.objects.get_or_create(
        username='life2launch',
        defaults={
            'email': 'admin@life2launch.org',
            'first_name': 'Life2Launch',
            'last_name': 'Team',
            'is_active': True,  # This is a valid organization account
        }
    )
    return life2launch_user


def get_or_create_shared_quest_template(quest_data, creator_user):
    """
    Get or create a shared quest template that can be enrolled in by multiple users.
    This creates the 'template' quest that users get enrolled in.
    """
    template_quest, created = Quest.objects.get_or_create(
        created_by=creator_user,
        user=creator_user,  # Template is owned by the creator
        title=quest_data['title'],
        template_id=None,  # This IS the template
        defaults={
            'description': quest_data['description'],
            'color': quest_data['color'],
            'editable': False,  # Shared quests are not editable by users
        }
    )

    if created:
        # Create milestones for the template
        milestone_objects = []
        for milestone_data in quest_data['milestones']:
            milestone = Milestone.objects.create(
                quest=template_quest,
                title=milestone_data['title'],
                description=milestone_data['description'],
                finish_date=milestone_data['finish_date'],
                status='not_started',
                order=milestone_data['order'],
            )
            milestone_objects.append(milestone)

        # Set up sequential prerequisites (each milestone depends on the previous one)
        for i, milestone in enumerate(milestone_objects):
            if i > 0:  # First milestone has no prerequisites
                milestone.prerequisites.add(milestone_objects[i - 1])

    return template_quest


def enroll_user_in_shared_quest(user, template_quest):
    """
    Enroll a user in a shared quest by creating a copy of the template quest
    assigned to the user.
    """
    # Check if user is already enrolled
    existing_quest = Quest.objects.filter(
        user=user,
        template_id=template_quest.id
    ).first()

    if existing_quest:
        return existing_quest

    # Create user's copy of the quest
    user_quest = Quest.objects.create(
        user=user,
        created_by=template_quest.created_by,
        template_id=template_quest.id,
        title=template_quest.title,
        description=template_quest.description,
        color=template_quest.color,
        editable=False,  # User cannot edit shared quests
    )

    # Copy milestones from template
    template_milestones = template_quest.milestones.all().order_by('order')
    milestone_mapping = {}  # Map template milestone to user milestone for prerequisites

    for template_milestone in template_milestones:
        user_milestone = Milestone.objects.create(
            quest=user_quest,
            title=template_milestone.title,
            description=template_milestone.description,
            finish_date=template_milestone.finish_date,
            status='not_started',
            order=template_milestone.order,
        )
        milestone_mapping[template_milestone.id] = user_milestone

    # Set up prerequisites based on template relationships
    for template_milestone in template_milestones:
        user_milestone = milestone_mapping[template_milestone.id]
        for prereq in template_milestone.prerequisites.all():
            if prereq.id in milestone_mapping:
                user_milestone.prerequisites.add(milestone_mapping[prereq.id])

    return user_quest


def create_personal_quest(user, quest_data):
    """
    Create a personal quest for the user (created by the user themselves).
    """
    # Check if this personal quest already exists
    existing_quest = Quest.objects.filter(
        user=user,
        created_by=user,
        title=quest_data['title'],
        template_id=None,  # Personal quests don't have template_id
    ).first()

    if existing_quest:
        return existing_quest

    personal_quest = Quest.objects.create(
        user=user,
        created_by=user,
        title=quest_data['title'],
        description=quest_data['description'],
        color=quest_data['color'],
        editable=True,  # Personal quests are editable
    )

    # Create milestones
    milestone_objects = []
    for milestone_data in quest_data['milestones']:
        milestone = Milestone.objects.create(
            quest=personal_quest,
            title=milestone_data['title'],
            description=milestone_data['description'],
            finish_date=milestone_data['finish_date'],
            status='not_started',
            order=milestone_data['order'],
        )
        milestone_objects.append(milestone)

    # Set up sequential prerequisites (each milestone depends on the previous one)
    for i, milestone in enumerate(milestone_objects):
        if i > 0:  # First milestone has no prerequisites
            milestone.prerequisites.add(milestone_objects[i - 1])

    return personal_quest


def initialize_default_quests_for_user(user):
    """
    Initialize default quests for a new user.
    This is called when a new user account is created.
    """
    if not settings.ENABLE_DEFAULT_QUESTS:
        return

    # 1. Create personal summer job quest
    summer_job_data = get_summer_job_quest_data()
    personal_quest = create_personal_quest(user, summer_job_data)

    # 2. Get or create life2launch organization user
    life2launch_user = get_or_create_life2launch_user()

    # 3. Get or create the shared "Getting Started" quest template
    getting_started_data = get_getting_started_quest_data()
    template_quest = get_or_create_shared_quest_template(getting_started_data, life2launch_user)

    # 4. Enroll user in the shared quest
    shared_quest = enroll_user_in_shared_quest(user, template_quest)

    return {
        'personal_quest': personal_quest,
        'shared_quest': shared_quest,
    }