import json
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.quests.models import Quest, Milestone

User = get_user_model()


class Command(BaseCommand):
    help = 'Load quest data from embedded JSON into database for admin user'

    def handle(self, *args, **options):
        # Embedded quest data from the frontend JSON file
        quest_data = {
            "Overview": {
                "id": "overview123",
                "title": "Quest Overview",
                "description": "Welcome to your personalized quest dashboard! Here you can track your progress across all your major life goals and aspirations. Each quest is designed to break down big dreams into manageable milestones, helping you build momentum and celebrate achievements along the way. By focusing on consistent progress rather than perfection, you'll develop the habits and skills needed to create the future you envision.",
                "milestones": []
            },
            "Finish High School": {
                "id": "abc123xyz",
                "title": "Finish High School",
                "description": "Completing your high school education is a foundational step that opens doors to higher education, career opportunities, and personal growth. This quest focuses on maintaining strong academic performance, developing study habits, and preparing for your next chapter. Each milestone builds essential skills like time management, critical thinking, and perseverance that will serve you throughout life.",
                "color": "#FF6B6B",
                "milestones": [
                    {
                        "id": "hs-1",
                        "date": "Mar 15",
                        "year": "2025",
                        "title": "Complete Junior Year with 3.5+ GPA",
                        "description": "Focus on core subjects and maintain consistent study habits. Complete all assignments on time and seek help when needed to ensure strong foundational knowledge.",
                        "status": "complete"
                    },
                    {
                        "id": "hs-2", 
                        "date": "Apr 10",
                        "year": "2025",
                        "title": "Take SAT/ACT Standardized Tests",
                        "description": "Prepare for and complete standardized testing. Study using prep materials, take practice tests, and schedule test dates well in advance of college application deadlines.",
                        "status": "complete"
                    },
                    {
                        "id": "hs-3",
                        "date": "May 15",
                        "year": "2025", 
                        "title": "Submit College Applications",
                        "description": "Research colleges, complete applications, write compelling essays, and gather letters of recommendation. Apply to a mix of reach, target, and safety schools.",
                        "status": "complete"
                    },
                    {
                        "id": "hs-4",
                        "date": "Jul 1",
                        "year": "2025",
                        "title": "Receive College Acceptance Letters",
                        "description": "Review admission decisions and financial aid packages. Compare options and make informed decisions about your next educational step.",
                        "status": "complete"
                    },
                    {
                        "id": "hs-5",
                        "date": "Sep 15",
                        "year": "2025",
                        "title": "Graduate High School",
                        "description": "Complete all graduation requirements, participate in senior activities, and celebrate this major milestone with family and friends.",
                        "status": "in_progress"
                    }
                ]
            },
            "Become a Veterinarian": {
                "id": "def456uvw",
                "title": "Become a Veterinarian", 
                "description": "Pursuing a career in veterinary medicine combines your love for animals with the satisfaction of helping them stay healthy and happy. This challenging but rewarding path requires dedication to science, compassion for animals, and strong communication skills with pet owners. Each milestone builds the knowledge, experience, and credentials needed to practice veterinary medicine.",
                "color": "#4ECDC4",
                "milestones": [
                    {
                        "id": "vet-1",
                        "date": "Mar 20",
                        "year": "2025",
                        "title": "Complete Advanced Biology and Chemistry",
                        "description": "Excel in prerequisite science courses including organic chemistry, biology, and physics. These subjects form the foundation for veterinary school admission and future coursework.",
                        "status": "complete"
                    },
                    {
                        "id": "vet-2",
                        "date": "May 25",
                        "year": "2025",
                        "title": "Gain Animal Care Experience",
                        "description": "Volunteer at local animal shelters, veterinary clinics, or farms to gain hands-on experience with different animal species and understand the day-to-day realities of animal care.",
                        "status": "complete"
                    },
                    {
                        "id": "vet-3",
                        "date": "Sep 1",
                        "year": "2025",
                        "title": "Start Pre-Veterinary Program",
                        "description": "Begin college coursework in a pre-veterinary track, focusing on required courses like anatomy, physiology, and animal nutrition while maintaining a high GPA.",
                        "status": "in_progress"
                    },
                    {
                        "id": "vet-4",
                        "date": "Dec 10",
                        "year": "2025",
                        "title": "Apply to Veterinary School",
                        "description": "Complete the Veterinary Medical College Application Service (VMCAS) application, including personal statements, transcripts, and veterinary experience documentation.",
                        "status": "not_started"
                    },
                    {
                        "id": "vet-5",
                        "date": "Feb 15",
                        "year": "2026",
                        "title": "Begin Doctor of Veterinary Medicine Program",
                        "description": "Start the 4-year DVM program, combining classroom learning with clinical rotations to develop comprehensive veterinary skills and knowledge.",
                        "status": "not_started"
                    }
                ]
            },
            "Travel to Mexico": {
                "id": "ghi789rst",
                "title": "Travel to Mexico",
                "description": "Planning your first international trip to Mexico is an exciting opportunity to experience new cultures, practice Spanish, and create lasting memories. This adventure will broaden your perspective, build confidence in navigating new environments, and develop valuable life skills like planning, budgeting, and cultural adaptation. Each milestone ensures you're prepared for a safe and enriching travel experience.",
                "color": "#45B7D1",
                "milestones": [
                    {
                        "id": "mexico-1",
                        "date": "Mar 25",
                        "year": "2025",
                        "title": "Research Destinations and Create Itinerary", 
                        "description": "Explore different regions of Mexico, research cultural sites, activities, and local customs. Create a preliminary itinerary that balances must-see attractions with authentic cultural experiences.",
                        "status": "complete"
                    },
                    {
                        "id": "mexico-2",
                        "date": "Apr 20",
                        "year": "2025",
                        "title": "Apply for Passport and Travel Documents",
                        "description": "Complete passport application process, gather required documentation, and ensure all travel documents will be valid for the duration of your trip.",
                        "status": "complete"
                    },
                    {
                        "id": "mexico-3",
                        "date": "Jun 5",
                        "year": "2025",
                        "title": "Learn Basic Spanish Phrases",
                        "description": "Study essential Spanish vocabulary and phrases for travel, dining, and emergency situations. Practice pronunciation and basic conversation skills.",
                        "status": "complete"
                    },
                    {
                        "id": "mexico-4",
                        "date": "Aug 10",
                        "year": "2025",
                        "title": "Save Money and Book Travel",
                        "description": "Reach savings goal for trip expenses, book flights and accommodations, and purchase travel insurance. Create a detailed budget for daily expenses.",
                        "status": "complete"
                    },
                    {
                        "id": "mexico-5",
                        "date": "Oct 20",
                        "year": "2025",
                        "title": "Embark on Mexico Adventure",
                        "description": "Depart for Mexico with confidence, embrace new experiences, try local foods, practice Spanish, and document memories through photos and journaling.",
                        "status": "in_progress"
                    }
                ]
            },
            "LIF101: Life Skills": {
                "id": "jkl012mno",
                "title": "LIF101: Life Skills",
                "description": "The Life Skills course is designed to prepare you for independent adult living by covering essential practical knowledge often not taught in traditional academic settings. From financial literacy to basic home maintenance, this comprehensive program builds confidence and competence in real-world situations. These skills will serve as a foundation for personal responsibility and success in all areas of life.",
                "color": "#96CEB4",
                "milestones": [
                    {
                        "id": "lif-1",
                        "date": "Mar 30",
                        "year": "2025",
                        "title": "Complete Personal Finance Module",
                        "description": "Learn budgeting, saving strategies, understanding credit, and basics of investing. Create a personal budget and open your first savings account.",
                        "status": "complete"
                    },
                    {
                        "id": "lif-2",
                        "date": "May 5",
                        "year": "2025",
                        "title": "Master Basic Cooking and Nutrition",
                        "description": "Learn to prepare healthy, balanced meals, understand nutrition labels, and develop meal planning skills. Practice cooking 5 different nutritious recipes.",
                        "status": "complete"
                    },
                    {
                        "id": "lif-3",
                        "date": "Jul 15",
                        "year": "2025",
                        "title": "Learn Home Maintenance Basics",
                        "description": "Understand basic repairs, cleaning techniques, and home safety. Practice skills like changing air filters, unclogging drains, and basic tool usage.",
                        "status": "complete"
                    },
                    {
                        "id": "lif-4",
                        "date": "Oct 1",
                        "year": "2025",
                        "title": "Develop Time Management and Organization",
                        "description": "Learn effective scheduling, goal setting, and organizational systems. Implement a personal productivity system and maintain it for 30 days.",
                        "status": "in_progress"
                    },
                    {
                        "id": "lif-5",
                        "date": "Dec 20",
                        "year": "2025",
                        "title": "Complete Final Project and Certification",
                        "description": "Demonstrate mastery of all life skills modules through a comprehensive final project. Receive certification of completion for your portfolio.",
                        "status": "not_started"
                    }
                ]
            },
            "Nike Tech Skills Challenge": {
                "id": "pqr345stu",
                "title": "Nike Tech Skills Challenge",
                "description": "The Nike Tech Skills Challenge is an innovative program that combines technology education with athletic inspiration, helping you develop digital literacy and technical skills needed for the modern workforce. Through hands-on projects and mentorship, you'll learn coding, design thinking, and innovation processes while building confidence in STEM fields. This program opens doors to technology careers and entrepreneurial opportunities.",
                "color": "#FECA57", 
                "milestones": [
                    {
                        "id": "nike-1",
                        "date": "Apr 1",
                        "year": "2025",
                        "title": "Complete Application and Selection Process",
                        "description": "Submit compelling application highlighting your interests in technology and innovation. Participate in interviews and selection activities to secure your spot in the program.",
                        "status": "complete"
                    },
                    {
                        "id": "nike-2",
                        "date": "Jun 15",
                        "year": "2025",
                        "title": "Learn Fundamentals of Coding",
                        "description": "Master basic programming concepts using Python or JavaScript. Complete coding challenges and build your first simple applications with mentor guidance.",
                        "status": "complete"
                    },
                    {
                        "id": "nike-3",
                        "date": "Aug 25",
                        "year": "2025",
                        "title": "Participate in Design Thinking Workshop",
                        "description": "Learn human-centered design principles and innovative problem-solving methodologies. Work in teams to identify user needs and prototype solutions.",
                        "status": "in_progress"
                    },
                    {
                        "id": "nike-4",
                        "date": "Nov 10",
                        "year": "2025",
                        "title": "Develop Capstone Technology Project",
                        "description": "Create an original technology solution addressing a real-world problem. Present your project to Nike mentors and industry professionals for feedback.",
                        "status": "not_started"
                    },
                    {
                        "id": "nike-5",
                        "date": "Jan 30",
                        "year": "2026",
                        "title": "Present at Nike Tech Showcase",
                        "description": "Demonstrate your completed project at the final showcase event. Network with Nike employees and receive mentorship for future technology career paths.",
                        "status": "not_started"
                    }
                ]
            }
        }

        # Get or create admin user
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Admin user not found. Please create admin user first.')
            )
            return

        # Create fake users for "Other" category quests
        fake_users = {}
        other_quest_creators = {
            'LIF101: Life Skills': 'life_skills_org',
            'Nike Tech Skills Challenge': 'nike_org'
        }

        for creator_username in other_quest_creators.values():
            fake_user, created = User.objects.get_or_create(
                username=creator_username,
                defaults={
                    'email': f'{creator_username}@example.com',
                    'first_name': creator_username.replace('_', ' ').title(),
                    'is_active': False,  # Mark as inactive since they're not real users
                }
            )
            fake_users[creator_username] = fake_user
            if created:
                self.stdout.write(f'  ✓ Created fake user: {creator_username}')

        self.stdout.write('Loading quest data...')

        # Track created objects for summary
        created_quests = 0
        created_milestones = 0

        for quest_key, quest_info in quest_data.items():
            # Skip Overview - it's not a real quest
            if quest_key == 'Overview':
                continue

            # Determine creator
            if quest_info['title'] in other_quest_creators:
                creator = fake_users[other_quest_creators[quest_info['title']]]
                editable = False  # Shared quests are not editable by default
            else:
                creator = admin_user
                editable = True

            # Create or update quest
            quest, quest_created = Quest.objects.get_or_create(
                user=admin_user,
                title=quest_info['title'],
                defaults={
                    'created_by': creator,
                    'description': quest_info['description'],
                    'color': quest_info['color'],
                    'editable': editable,
                    'template_id': None,  # These are original instances
                }
            )

            if quest_created:
                created_quests += 1
                self.stdout.write(f'  ✓ Created quest: {quest.title}')
            else:
                # Update existing quest
                quest.description = quest_info['description']
                quest.color = quest_info['color']
                quest.created_by = creator
                quest.editable = editable
                quest.save()
                self.stdout.write(f'  ↻ Updated quest: {quest.title}')

            # Clear existing milestones for clean reload
            quest.milestones.all().delete()

            # Create milestones
            milestone_objects = []
            for index, milestone_info in enumerate(quest_info['milestones']):
                # Parse date from "Mar 15" and "2025" format
                try:
                    date_str = f"{milestone_info['date']} {milestone_info['year']}"
                    finish_date = datetime.strptime(date_str, '%b %d %Y').date()
                except (ValueError, KeyError):
                    # Fallback date if parsing fails
                    finish_date = datetime(2025, 12, 31).date()

                milestone = Milestone.objects.create(
                    quest=quest,
                    title=milestone_info['title'],
                    description=milestone_info['description'],
                    finish_date=finish_date,
                    status=milestone_info['status'],
                    order=index + 1,  # 1-based ordering
                )
                milestone_objects.append(milestone)
                created_milestones += 1

            # Set up prerequisite relationships (each milestone depends on the previous one)
            for i, milestone in enumerate(milestone_objects):
                if i > 0:  # First milestone has no prerequisites
                    milestone.prerequisites.add(milestone_objects[i - 1])

            self.stdout.write(f'    → Created {len(milestone_objects)} milestones')

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Successfully loaded quest data!\n'
                f'   Created: {created_quests} quests, {created_milestones} milestones\n'
                f'   All quests assigned to: {admin_user.username}'
            )
        )

        # Show quest categories
        personal_quests = Quest.objects.filter(user=admin_user, created_by=admin_user)
        other_quests = Quest.objects.filter(user=admin_user).exclude(created_by=admin_user)
        
        self.stdout.write(f'\n📊 Quest Categories:')
        self.stdout.write(f'   Personal: {personal_quests.count()} quests')
        self.stdout.write(f'   Other: {other_quests.count()} quests')
        
        # Show in-progress milestones
        in_progress = Milestone.objects.filter(quest__user=admin_user, status='in_progress')
        self.stdout.write(f'   In Progress: {in_progress.count()} milestones')