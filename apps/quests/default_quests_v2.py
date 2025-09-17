"""
Default quest data for new user initialization - V2 Enrollment System.
This module contains the default quest templates and enrollment logic for the new enrollment-based system.
"""
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import QuestTemplate, MilestoneTemplate, QuestEnrollment, MilestoneProgress

User = get_user_model()


def get_summer_job_quest_template_data():
    """
    Returns the summer job quest template data structure.
    This quest is personal (created by the user themselves).
    """
    return {
        'title': 'Land a Summer Job',
        'description': 'A comprehensive quest to help you secure a meaningful summer internship or job opportunity. This quest will guide you through all the essential steps from self-assessment to landing the role.',
        'color': '#4CAF50',  # Green
        'category': 'Personal',
        'is_shared': False,  # Personal quests are not shared
        'milestones': [
            {
                'title': 'Complete Self-Assessment',
                'description': 'Identify your interests, strengths, skills, and career goals. Use career assessment tools and reflect on what type of summer role would be most valuable for your development.',
                'estimated_finish_days': 7,
                'order': 1,
            },
            {
                'title': 'Research Target Industries & Roles',
                'description': 'Research 3-5 industries and specific job roles that align with your interests and goals. Create a list of companies you\'d like to work for.',
                'estimated_finish_days': 14,
                'order': 2,
            },
            {
                'title': 'Update Resume & Portfolio',
                'description': 'Create or update your resume to highlight relevant experiences, skills, and achievements. If applicable, build or update your portfolio with relevant projects.',
                'estimated_finish_days': 21,
                'order': 3,
            },
            {
                'title': 'Craft Cover Letter Templates',
                'description': 'Write 2-3 cover letter templates that you can customize for different types of roles and industries you\'re targeting.',
                'estimated_finish_days': 28,
                'order': 4,
            },
            {
                'title': 'Network & Seek Referrals',
                'description': 'Reach out to your network (family, friends, professors, alumni) to let them know you\'re looking for summer opportunities. Ask for introductions and advice.',
                'estimated_finish_days': 35,
                'order': 5,
            },
            {
                'title': 'Apply to Target Positions',
                'description': 'Apply to 10-15 summer positions that match your criteria. Track your applications in a spreadsheet with company names, positions, and application dates.',
                'estimated_finish_days': 49,
                'order': 6,
            },
            {
                'title': 'Prepare for Interviews',
                'description': 'Practice common interview questions, research the companies you\'ve applied to, and prepare thoughtful questions to ask interviewers.',
                'estimated_finish_days': 56,
                'order': 7,
            },
            {
                'title': 'Complete Interview Process',
                'description': 'Attend interviews, send thank-you notes, and follow up appropriately with potential employers.',
                'estimated_finish_days': 70,
                'order': 8,
            },
            {
                'title': 'Evaluate & Accept Offer',
                'description': 'Review job offers, negotiate if appropriate, and make your final decision. Confirm start date and any pre-employment requirements.',
                'estimated_finish_days': 84,
                'order': 9,
            }
        ]
    }


def get_getting_started_quest_template_data():
    """
    Returns the getting started quest template data structure.
    This quest is shared (created by life2launch organization).
    """
    return {
        'title': 'Getting Started: Discover Your Path',
        'description': 'Welcome to Life2Launch! This foundational quest will help you explore your values, strengths, and goals as you begin your journey toward meaningful career and life choices.',
        'color': '#2196F3',  # Blue
        'category': 'Life2Launch',
        'is_shared': True,  # Shared quest
        'milestones': [
            {
                'title': 'Complete Your Profile',
                'description': 'Fill out your Life2Launch profile with basic information about yourself, your interests, and your current stage in life.',
                'estimated_finish_days': 3,
                'order': 1,
            },
            {
                'title': 'Values Assessment',
                'description': 'Complete the values assessment to identify what matters most to you in work and life. Understanding your core values will guide your decision-making.',
                'estimated_finish_days': 10,
                'order': 2,
            },
            {
                'title': 'Strengths Discovery',
                'description': 'Take the strengths assessment to identify your natural talents and abilities. Learn how to leverage these strengths in your career planning.',
                'estimated_finish_days': 17,
                'order': 3,
            },
            {
                'title': 'Goal Setting Workshop',
                'description': 'Learn the fundamentals of effective goal setting using the SMART criteria. Set 3 short-term and 2 long-term goals for yourself.',
                'estimated_finish_days': 24,
                'order': 4,
            },
            {
                'title': 'Create Your Vision Board',
                'description': 'Combine your values, strengths, and goals to create a personal vision board that represents your ideal future.',
                'estimated_finish_days': 31,
                'order': 5,
            },
            {
                'title': 'Connect with Mentors',
                'description': 'Explore the mentor network and connect with 1-2 mentors who align with your interests and goals.',
                'estimated_finish_days': 38,
                'order': 6,
            },
            {
                'title': 'Plan Your Next Steps',
                'description': 'Based on your self-discovery, create an action plan for the next 3 months. Identify specific quests and activities you want to pursue.',
                'estimated_finish_days': 45,
                'order': 7,
            }
        ]
    }


def get_or_create_life2launch_user():
    """
    Get or create the life2launch organization user.
    This user represents the organization that creates shared quest templates.
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


def create_quest_template(template_data, creator_user):
    """
    Create a quest template with its milestone templates.
    Returns the created quest template.
    """
    # Check if template already exists
    existing_template = QuestTemplate.objects.filter(
        created_by=creator_user,
        title=template_data['title']
    ).first()

    if existing_template:
        return existing_template

    # Create the quest template
    quest_template = QuestTemplate.objects.create(
        title=template_data['title'],
        description=template_data['description'],
        color=template_data['color'],
        category=template_data['category'],
        created_by=creator_user,
        is_shared=template_data['is_shared'],
    )

    # Create milestone templates
    milestone_templates = []
    for milestone_data in template_data['milestones']:
        milestone_template = MilestoneTemplate.objects.create(
            quest_template=quest_template,
            title=milestone_data['title'],
            description=milestone_data['description'],
            order=milestone_data['order'],
            estimated_finish_days=milestone_data['estimated_finish_days'],
        )
        milestone_templates.append(milestone_template)

    # Set up sequential prerequisites (each milestone depends on the previous one)
    for i, milestone_template in enumerate(milestone_templates):
        if i > 0:  # First milestone has no prerequisites
            milestone_template.prerequisites.add(milestone_templates[i - 1])

    return quest_template


def enroll_user_in_quest_template(user, quest_template):
    """
    Enroll a user in a quest template by creating a QuestEnrollment
    and MilestoneProgress records for each milestone.
    """
    # Check if user is already enrolled
    existing_enrollment = QuestEnrollment.objects.filter(
        user=user,
        quest_template=quest_template
    ).first()

    if existing_enrollment:
        return existing_enrollment

    # Create the enrollment
    enrollment = QuestEnrollment.objects.create(
        user=user,
        quest_template=quest_template,
        status='active'
    )

    # Create milestone progress records
    milestone_templates = quest_template.milestone_templates.all().order_by('order')
    for milestone_template in milestone_templates:
        # Calculate finish date based on enrollment date + estimated days
        finish_date = enrollment.enrolled_at.date() + timedelta(days=milestone_template.estimated_finish_days)

        MilestoneProgress.objects.create(
            enrollment=enrollment,
            milestone_template=milestone_template,
            status='not_started',
            finish_date=finish_date
        )

    return enrollment


def initialize_default_quests_for_user_v2(user):
    """
    Initialize default quest templates and enroll user in them.
    This is the V2 version using the new enrollment system.
    """
    if not settings.ENABLE_DEFAULT_QUESTS:
        return

    # 1. Create personal summer job quest template and enroll user
    summer_job_data = get_summer_job_quest_template_data()
    personal_template = create_quest_template(summer_job_data, user)
    personal_enrollment = enroll_user_in_quest_template(user, personal_template)

    # 2. Get the existing shared "Getting Started" quest template
    life2launch_user = get_or_create_life2launch_user()

    # Look for existing shared template first
    from .models import QuestTemplate
    shared_template = QuestTemplate.objects.filter(
        created_by=life2launch_user,
        title="Getting Started: Discover Your Path",
        is_shared=True
    ).first()

    # If not found, create it
    if not shared_template:
        getting_started_data = get_getting_started_quest_template_data()
        shared_template = create_quest_template(getting_started_data, life2launch_user)

    # 3. Enroll user in the shared quest template
    shared_enrollment = enroll_user_in_quest_template(user, shared_template)

    return {
        'personal_template': personal_template,
        'personal_enrollment': personal_enrollment,
        'shared_template': shared_template,
        'shared_enrollment': shared_enrollment,
    }