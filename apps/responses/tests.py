from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.courses.models import Course
from .models import CourseSession, QuestionResponse, ConversationTurn
from .utils import parse_agenda_items, generate_question_id, validate_agenda_format

User = get_user_model()


class ResponseModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.course = Course.objects.create(
            id='test_course',
            title='Test Course',
            description='A test course',
            agenda='''# Agenda

## About
Test agenda for testing purposes.

## Items
### 1. Test Question
What is your test answer? (short answer)

### 2. Another Question
Tell us more about testing. (long answer)''',
            x_position=100,
            y_position=100,
            order=1
        )
    
    def test_course_session_creation(self):
        session = CourseSession.objects.create(
            user=self.user,
            course=self.course,
            character_used='minu'
        )
        
        self.assertEqual(session.status, 'active')
        self.assertEqual(session.total_questions, 2)
        self.assertEqual(session.answered_questions, 0)
        self.assertEqual(session.completion_percentage, 0.0)
        self.assertIsNotNone(session.agenda_version_hash)
        self.assertIsNotNone(session.agenda_snapshot)
    
    def test_question_response_creation(self):
        session = CourseSession.objects.create(
            user=self.user,
            course=self.course
        )
        
        response = QuestionResponse.objects.create(
            session=session,
            question_number=1,
            question_id='test_question',
            question_text='What is your test answer?',
            raw_response='This is my test answer',
            processed_response='This is my test answer',
            status='complete'
        )
        
        self.assertEqual(response.status, 'complete')
        self.assertIsNotNone(response.completed_at)
        
        # Check that session progress was updated
        session.refresh_from_db()
        self.assertEqual(session.answered_questions, 1)
        self.assertEqual(session.completion_percentage, 50.0)
    
    def test_conversation_turn_creation(self):
        session = CourseSession.objects.create(
            user=self.user,
            course=self.course
        )
        
        turn = ConversationTurn.objects.create(
            session=session,
            turn_number=1,
            role='user',
            content='Hello, I want to start the assessment'
        )
        
        self.assertEqual(turn.role, 'user')
        self.assertEqual(turn.turn_number, 1)


class UtilsTestCase(TestCase):
    def test_parse_agenda_items(self):
        agenda = '''# Agenda

## About
This is a test agenda.

## Items
### 1. Career Goals
What are your career goals? (short answer)

### 2. Personal Growth
Describe your personal growth plans. (long answer)'''
        
        parsed = parse_agenda_items(agenda)
        
        self.assertEqual(parsed['about'], 'This is a test agenda.')
        self.assertEqual(len(parsed['items']), 2)
        self.assertEqual(parsed['items'][0]['title'], 'Career Goals')
        self.assertEqual(parsed['items'][0]['question_id'], 'career_goals')
        self.assertEqual(parsed['items'][1]['title'], 'Personal Growth')
        self.assertEqual(parsed['items'][1]['question_id'], 'personal_growth')
    
    def test_generate_question_id(self):
        self.assertEqual(generate_question_id('Career Goals'), 'career_goals')
        self.assertEqual(generate_question_id('Personal Growth & Development'), 'personal_growth_development')
        self.assertEqual(generate_question_id('Test-Question!'), 'testquestion')
    
    def test_validate_agenda_format(self):
        valid_agenda = '''# Agenda

## About
Valid agenda.

## Items
### 1. Question One
First question

### 2. Question Two
Second question'''
        
        result = validate_agenda_format(valid_agenda)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['issues']), 0)
        self.assertEqual(result['item_count'], 2)
        
        # Test invalid agenda
        invalid_agenda = '''# Agenda
### 1. Question without proper structure'''
        
        result = validate_agenda_format(invalid_agenda)
        self.assertFalse(result['valid'])
        self.assertTrue(len(result['issues']) > 0)