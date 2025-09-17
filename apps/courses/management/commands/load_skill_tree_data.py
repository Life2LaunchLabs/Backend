from django.core.management.base import BaseCommand
from apps.courses.models import Course, UserCourseProgress
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Load skill tree course data'

    def handle(self, *args, **options):
        # Clear existing data
        Course.objects.all().delete()
        
        # Skill tree structure based on SVG constellation
        # Coordinates are for 1024x1024 viewBox
        courses_data = [
            # Root node - bottom center
            {
                'id': 'intro',
                'title': 'Introduction to Self Discovery',
                'description': 'Begin your journey of personal growth and self-awareness. This foundational course introduces you to the core concepts and practices that will guide your development.',
                'agenda': '''# Agenda

## About
Welcome to your journey of self-discovery! This introductory session will help you understand the path ahead and set intentions for your growth.

## Items
### 1. Personal motivation
What drew you to start this journey of self-discovery? What do you hope to gain? (short answer)

### 2. Current perspective
How would you describe yourself in three words right now? (short answer)''',
                'parent': None,
                'x_position': 512,  # Center X
                'y_position': 800,  # Bottom
                'order': 0
            },
            
            # Second level - mid center (three tight nodes)
            {
                'id': 'inner_world',
                'title': 'Inner World',
                'description': 'Explore your internal landscape - thoughts, emotions, values, and beliefs. Learn to understand and navigate your inner self.',
                'agenda': '''# Agenda

## About
This is the first of a series of assessments designed to help the user uncover insights into themselves and their inner world through visualization. This assessment is about their dreams and ambitions, future assessments will cover their hobbies and interests, and culture and values.

You, as the character conducting this assessment, do not see it as an assessment. This is a conversation with a friend (the user) in which you are trying to learn more about what is important to them. Although there is a set agenda, you (the character) are not aware of it, and will introduce topics naturally as you progress through them.

The items under the agenda represent assessment questions that need to be answered, along with instructions regarding response type. Work through them in order, rephrasing the questions to your characters own natural conversational tone. They should be worked into conversation naturally, following on from what the user says, as if curious to learn more. If the user asks questions of their own or asks for your advice, engage with them and attempt to help, however try to steer the conversation back to the agenda when possible and try to ensure that the answers come from them, not from you.

In some cases, the user may take multiple responses to answer a question, or require prompting via yes/no/simple options. In this case, once you deem they have completely answered a question, compose their responses into a single answer. Use direct quotes as much as possible, but phrase the entire response as if written by the user.

## Items
### 1. Career Aspirations
Imagine yourself in your ideal job setting. What does it look like? what accomplishments are you most proud of in this vision? (short answer)

### 2. Reflecting on Education
Picture yourself achieving your next educational milestone. What are you learning about? How does it feel to learn and grow in this area? (short answer)

### 3. Personal growth
Think about personal qualities you wish to develop. envision yourself embodying these qualities. what activities are you engaging in that contribute to your personal growth? (short answer)

### 4. Integration and gratitude
Take a minute to imagine bringing all these aspects together into a harmonious whole. Feel a sense of gratitude for your current achievements, and excitement for the potential to reach these envisioned goals. What ideas or feelings arose during this session? (short answer)

### 5. Reflection
What specific goals felt particularly important to you? what first steps might you take to achieve them? (short answer)''',
                'parent': 'intro',
                'x_position': 412,  # Left of center
                'y_position': 550,  # Mid
                'order': 1
            },
            {
                'id': 'outer_world',
                'title': 'Outer World', 
                'description': 'Understand your environment, relationships, and how you interact with the world around you. Build meaningful connections.',
                'agenda': '''# Agenda

## About
Explore how you connect with the world around you - your relationships, community, and impact.

## Items
### 1. Relationship reflection
What relationships in your life bring you the most joy and fulfillment? (short answer)

### 2. Community connection
How do you like to contribute to your community or the world around you? (short answer)

### 3. Future connections
What kind of relationships or communities do you hope to build in the future? (short answer)''',
                'parent': 'intro',
                'x_position': 512,  # Center
                'y_position': 550,  # Mid
                'order': 2
            },
            {
                'id': 'taking_action',
                'title': 'Taking Action',
                'description': 'Transform insights into action. Learn to set goals, build habits, and create lasting change in your life.',
                'agenda': '''# Agenda

## About
Learn how to turn your insights and dreams into concrete actions and lasting change.

## Items
### 1. Goal reflection
What's one important goal you've been thinking about but haven't started yet? (short answer)

### 2. Action barriers
What usually stops you from taking action on things that matter to you? (short answer)

### 3. Small steps
What's the smallest step you could take today toward one of your goals? (short answer)''',
                'parent': 'intro',
                'x_position': 612,  # Right of center
                'y_position': 550,  # Mid
                'order': 3
            },
            
            # Third level - Inner World children (mid left cluster)
            {
                'id': 'emotions_mastery',
                'title': 'Emotions Mastery',
                'description': 'Develop emotional intelligence and learn to work with your emotions as allies rather than obstacles.',
                'agenda': '''# Agenda

## About
Explore your relationship with emotions and develop skills to work with them effectively.

## Items
### 1. Emotional awareness
What emotions do you find most challenging to handle? (short answer)

### 2. Emotional triggers
What situations tend to bring up strong emotions for you? (short answer)''',
                'parent': 'inner_world',
                'x_position': 300,  # Left cluster - moved right by 20
                'y_position': 320,  # Moved up by 30
                'order': 4
            },
            {
                'id': 'values_clarity',
                'title': 'Values Clarity',
                'description': 'Identify and clarify your core values. Align your decisions and actions with what matters most to you.',
                'agenda': '''# Agenda

## About
Discover what truly matters to you and how to live in alignment with your values.

## Items
### 1. Core values
What principles or values are most important to you in life? (short answer)

### 2. Values in action
How do these values show up in your daily decisions? (short answer)''',
                'parent': 'inner_world',
                'x_position': 350,
                'y_position': 300,
                'order': 5
            },
            {
                'id': 'mindful_awareness',
                'title': 'Mindful Awareness',
                'description': 'Cultivate present-moment awareness and develop a deeper understanding of your thought patterns.',
                'agenda': '''# Agenda

## About
Develop awareness of your thoughts and learn to be present in each moment.

## Items
### 1. Mind patterns
What thoughts or mental patterns do you notice repeating in your mind? (short answer)

### 2. Present moment
When do you feel most present and aware? (short answer)''',
                'parent': 'inner_world',
                'x_position': 420,
                'y_position': 350,
                'order': 6
            },
            
            # Third level - Outer World children (upper center cluster)
            {
                'id': 'communication_skills',
                'title': 'Communication Skills',
                'description': 'Master the art of clear, empathetic communication. Learn to express yourself and truly listen to others.',
                'agenda': '''# Agenda

## About
Improve how you express yourself and connect with others through communication.

## Items
### 1. Communication style
How would you describe your natural communication style? (short answer)

### 2. Listening skills
What makes you feel truly heard and understood by others? (short answer)''',
                'parent': 'outer_world',
                'x_position': 450,
                'y_position': 200,
                'order': 7
            },
            {
                'id': 'relationship_building',
                'title': 'Relationship Building',
                'description': 'Build and maintain healthy, meaningful relationships in all areas of your life.',
                'agenda': '''# Agenda

## About
Learn how to build and nurture meaningful relationships in all areas of your life.

## Items
### 1. Relationship qualities
What qualities do you value most in close relationships? (short answer)

### 2. Connection challenges
What do you find most challenging about building new relationships? (short answer)''',
                'parent': 'outer_world',
                'x_position': 512,
                'y_position': 150,
                'order': 8
            },
            {
                'id': 'social_impact',
                'title': 'Social Impact',
                'description': 'Learn how to create positive change in your community and contribute to something larger than yourself.',
                'agenda': '''# Agenda

## About
Explore how you can contribute to positive change in your community and the world.

## Items
### 1. Impact vision
What kind of positive impact do you want to have on the world? (short answer)

### 2. Community involvement
How do you currently (or want to) contribute to your community? (short answer)''',
                'parent': 'outer_world',
                'x_position': 574,
                'y_position': 200,
                'order': 9
            },
            
            # Third level - Taking Action children (mid right cluster)
            {
                'id': 'goal_setting',
                'title': 'Goal Setting',
                'description': 'Learn to set meaningful, achievable goals and create step-by-step plans to reach them.',
                'agenda': '''# Agenda

## About
Learn how to set meaningful goals and create plans to achieve them.

## Items
### 1. Goal priorities
What's one big goal you'd love to achieve in the next year? (short answer)

### 2. Goal barriers
What typically gets in the way of achieving your goals? (short answer)''',
                'parent': 'taking_action',
                'x_position': 680,
                'y_position': 350,
                'order': 10
            },
            {
                'id': 'habit_formation',
                'title': 'Habit Formation',
                'description': 'Master the science of habit formation. Build positive habits and break limiting patterns.',
                'agenda': '''# Agenda

## About
Explore how to build helpful habits and change patterns that no longer serve you.

## Items
### 1. Positive habits
What's one habit you'd like to develop to improve your life? (short answer)

### 2. Habit challenges
What makes it difficult for you to stick to new habits? (short answer)''',
                'parent': 'taking_action',
                'x_position': 750,
                'y_position': 300,
                'order': 11
            },
            {
                'id': 'resilience_building',
                'title': 'Resilience Building',
                'description': 'Develop resilience and learn to bounce back from setbacks stronger than before.',
                'agenda': '''# Agenda

## About
Build your ability to bounce back from challenges and grow stronger through adversity.

## Items
### 1. Resilience strengths
Think of a difficult time you overcame - what helped you get through it? (short answer)

### 2. Growth mindset
How do you typically respond to setbacks or failures? (short answer)''',
                'parent': 'taking_action',
                'x_position': 820,
                'y_position': 350,
                'order': 12
            }
        ]
        
        # Create all courses first (without parent relationships)
        created_courses = {}
        courses_data_copy = []
        for course_data in courses_data:
            course_data_copy = course_data.copy()
            courses_data_copy.append(course_data_copy)
            parent_id = course_data_copy.pop('parent')
            course = Course.objects.create(**course_data_copy)
            created_courses[course.id] = course
            self.stdout.write(f"Created course: {course.title}")
        
        # Set parent relationships in a second pass
        for course_data in courses_data:
            if course_data.get('parent'):
                child_course = created_courses[course_data['id']]
                parent_course = created_courses[course_data['parent']]
                child_course.parent = parent_course
                child_course.save()
                self.stdout.write(f"Set parent: {child_course.title} -> {parent_course.title}")
        
        # Create user progress for the admin user with demo data
        try:
            admin_user = User.objects.get(username='admin')
            
            # Set intro and outer_world to complete as per requirements
            intro_course = created_courses['intro']
            outer_world_course = created_courses['outer_world']
            
            UserCourseProgress.objects.create(
                user=admin_user,
                course=intro_course,
                status='complete'
            )
            
            UserCourseProgress.objects.create(
                user=admin_user,
                course=outer_world_course,
                status='complete'
            )
            
            self.stdout.write("Set demo progress for admin user")
            
        except User.DoesNotExist:
            self.stdout.write("Admin user not found - skipping demo progress setup")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {len(courses_data)} courses for skill tree')
        )