# Create JSON files for the five demo activities based on the user's current command.
import json, os, textwrap

base_path = "./"
os.makedirs(base_path, exist_ok=True)

def write_json(filename, data):
    path = os.path.join(base_path, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

# 1) Pathways Assessment (comprehensive) -------------------------------
pathways = {
  "activity": {"slug": "pathways-assessment", "status": "published"},
  "version": {
    "number": 1,
    "title": "Pathways Assessment",
    "description": "Experience the complete range of Activities features including media blocks, diverse question types, and interactive content.",
    "is_published": True,
    "meta": {
      "estimated_duration": "5 minutes",
      "difficulty": "beginner_to_intermediate",
      "topics": ["mindfulness", "self-reflection", "decision-making", "goal-setting"]
    }
  },
  "media_assets": [
    {
      "filename": "peaceful_environment.png",
      "path": "activity_media/illustrations/peaceful_environment.png",
      "title": "Peaceful Environment",
      "description": "A calming, serene environment for reflection",
      "mime_type": "image/png",
      "alt_text": "A calming, serene environment for reflection"
    },
    {
      "filename": "reflection_example.png",
      "path": "activity_media/examples/reflection_example.png",
      "title": "Reflection Journal",
      "description": "Example of personal reflection and journaling",
      "mime_type": "image/png",
      "alt_text": "Example of personal reflection and journaling"
    },
    {
      "filename": "discovery_concept.png",
      "path": "activity_media/illustrations/discovery_concept.png",
      "title": "Discovery and Learning",
      "description": "Illustration representing discovery and exploration",
      "mime_type": "image/png",
      "alt_text": "Illustration representing discovery and exploration"
    },
    {
      "filename": "choice_scenario.png",
      "path": "activity_media/examples/choice_scenario.png",
      "title": "Decision Making Scenario",
      "description": "Visual example of making choices and decisions",
      "mime_type": "image/png",
      "alt_text": "Visual example of making choices and decisions"
    },
    {
      "filename": "progress_visualization.png",
      "path": "activity_media/interface_demos/progress_visualization.png",
      "title": "Progress and Growth",
      "description": "Visualization of learning progress and skill development",
      "mime_type": "image/png",
      "alt_text": "Visualization of learning progress and skill development"
    },
    {
      "filename": "future_concept.png",
      "path": "activity_media/examples/future_concept.png",
      "title": "Future Possibilities",
      "description": "Conceptual image representing future opportunities",
      "mime_type": "image/png",
      "alt_text": "Conceptual image representing future opportunities"
    }
  ],
  "pages": [
    {
      "index": 0,
      "title": "Welcome to Your Mindfulness Journey",
      "meta": {"page_type": "introduction"},
      "blocks": [
        {
          "index": 0,
          "block_type": "text",
          "config": {"style": "h1", "content": "Welcome to Your Mindfulness Journey"}
        },
        {
          "index": 1,
          "block_type": "media",
          "config": {
            "media_filename": "peaceful_environment.png",
            "caption": "Take a moment to center yourself as we begin this journey together.",
            "size": "large"
          }
        },
        {
          "index": 2,
          "block_type": "text",
          "config": {
            "style": "body",
            "content": "This comprehensive assessment will guide you through various aspects of mindfulness and self-reflection. You'll encounter different types of questions, interactive elements, and visual content designed to help you explore your thoughts, feelings, and goals."
          }
        },
        {
          "index": 3,
          "block_type": "text",
          "config": {
            "style": "lead",
            "content": "Take your time with each section. There are no right or wrong answers—this is about your personal journey and insights."
          }
        }
      ]
    },
    {
      "index": 1,
      "title": "Personal Reflection",
      "meta": {"page_type": "reflection"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Personal Reflection & Self-Awareness"}},
        {
          "index": 1,
          "block_type": "media",
          "config": {
            "media_filename": "reflection_example.png",
            "caption": "Reflection is the foundation of mindful living.",
            "size": "medium"
          }
        },
        {
          "index": 2,
          "block_type": "question",
          "config": {
            "question_id": "current_mood",
            "question_type": "text_input",
            "question_text": "How would you describe your current emotional state in a few words?",
            "placeholder": "Take a moment to check in with yourself...",
            "required": True
          }
        },
        {
          "index": 3,
          "block_type": "question",
          "config": {
            "question_id": "mindfulness_frequency",
            "question_type": "multiple_choice",
            "question_text": "How often do you practice mindfulness or meditation?",
            "options": [
              {"value": "daily", "label": "Daily"},
              {"value": "weekly", "label": "Several times a week"},
              {"value": "monthly", "label": "A few times a month"},
              {"value": "rarely", "label": "Rarely or never"},
              {"value": "just_starting", "label": "I'm just starting to explore it"}
            ],
            "required": True
          }
        },
        {
          "index": 4,
          "block_type": "question",
          "config": {
            "question_id": "gratitude_reflection",
            "question_type": "text_input",
            "question_text": "What are three things you're grateful for today? Take a moment to really consider why each one matters to you.",
            "placeholder": "1. ...\n2. ...\n3. ...",
            "multiline": True,
            "required": False
          }
        }
      ]
    },
    {
      "index": 2,
      "title": "Mindful Decision Making",
      "meta": {"page_type": "assessment"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Mindful Decision Making"}},
        {
          "index": 1,
          "block_type": "media",
          "config": {
            "media_filename": "discovery_concept.png",
            "caption": "Every choice is an opportunity for growth and discovery.",
            "size": "medium"
          }
        },
        {
          "index": 2,
          "block_type": "text",
          "config": {"style": "body", "content": "Consider the following scenarios and reflect on how mindfulness might guide your choices."}
        },
        {
          "index": 3,
          "block_type": "question",
          "config": {
            "question_id": "stress_response",
            "question_type": "single_choice",
            "question_text": "You're facing a stressful deadline at work. Which approach feels most aligned with mindful living?",
            "options": [
              {"value": "rush_panic", "label": "Rush through tasks, accepting stress as inevitable"},
              {"value": "pause_breathe", "label": "Pause, take three deep breaths, then prioritize mindfully"},
              {"value": "avoid_procrastinate", "label": "Avoid the stress by procrastinating or distraction"},
              {"value": "push_through", "label": "Push through with determination, ignoring physical/emotional signals"}
            ],
            "required": True
          }
        },
        {
          "index": 4,
          "block_type": "media",
          "config": {
            "media_filename": "choice_scenario.png",
            "caption": "Mindful choices create ripple effects in our lives.",
            "size": "small"
          }
        },
        {
          "index": 5,
          "block_type": "question",
          "config": {
            "question_id": "core_values",
            "question_type": "multiple_choice",
            "question_text": "Which values are most important to you in daily life? (Select all that apply)",
            "options": [
              {"value": "compassion", "label": "Compassion and kindness"},
              {"value": "authenticity", "label": "Authenticity and honesty"},
              {"value": "growth", "label": "Personal growth and learning"},
              {"value": "connection", "label": "Connection and relationships"},
              {"value": "peace", "label": "Inner peace and calm"},
              {"value": "purpose", "label": "Sense of purpose and meaning"},
              {"value": "balance", "label": "Work-life balance"},
              {"value": "creativity", "label": "Creativity and expression"}
            ],
            "required": False,
            "multiple_selection": True
          }
        }
      ]
    },
    {
      "index": 3,
      "title": "Mindful Goal Setting",
      "meta": {"page_type": "planning"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Mindful Goal Setting & Intentions"}},
        {
          "index": 1,
          "block_type": "media",
          "config": {
            "media_filename": "progress_visualization.png",
            "caption": "Growth happens step by step, with mindful intention.",
            "size": "large"
          }
        },
        {
          "index": 2,
          "block_type": "text",
          "config": {"style": "body", "content": "Mindful goal setting involves setting intentions that align with your values and current capacity for growth."}
        },
        {
          "index": 3,
          "block_type": "question",
          "config": {
            "question_id": "mindfulness_intention",
            "question_type": "text_input",
            "question_text": "What is one mindfulness practice or habit you'd like to cultivate over the next month?",
            "placeholder": "Be specific and realistic...",
            "required": True
          }
        },
        {
          "index": 4,
          "block_type": "question",
          "config": {
            "question_id": "support_preference",
            "question_type": "single_choice",
            "question_text": "How do you prefer to stay accountable to your mindfulness goals?",
            "options": [
              {"value": "self_reflection", "label": "Regular self-reflection and journaling"},
              {"value": "accountability_partner", "label": "An accountability partner or friend"},
              {"value": "structured_program", "label": "A structured program or course"},
              {"value": "community_group", "label": "A mindfulness community or group"},
              {"value": "apps_reminders", "label": "Apps, reminders, or digital tools"},
              {"value": "flexible_approach", "label": "I prefer a flexible, intuitive approach"}
            ],
            "required": True
          }
        },
        {
          "index": 5,
          "block_type": "question",
          "config": {
            "question_id": "anticipated_challenges",
            "question_type": "text_input",
            "question_text": "What challenges do you anticipate in maintaining your mindfulness practice? How might you work with them compassionately?",
            "placeholder": "Consider both external obstacles and internal resistance...",
            "multiline": True,
            "required": False
          }
        }
      ]
    },
    {
      "index": 4,
      "title": "Your Path Forward",
      "meta": {"page_type": "conclusion"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Your Mindful Path Forward"}},
        {
          "index": 1,
          "block_type": "media",
          "config": {
            "media_filename": "future_concept.png",
            "caption": "Every moment offers a fresh opportunity for mindful awareness.",
            "size": "medium"
          }
        },
        {
          "index": 2,
          "block_type": "text",
          "config": {
            "style": "body",
            "content": "Thank you for taking this journey of self-reflection and mindful exploration. The insights you've gained here are just the beginning."
          }
        },
        {
          "index": 3,
          "block_type": "text",
          "config": {
            "style": "quote",
            "content": "Remember: Mindfulness is not about perfection—it's about presence, compassion, and gentle awareness of each moment as it unfolds."
          }
        },
        {
          "index": 4,
          "block_type": "question",
          "config": {
            "question_id": "closing_reflection",
            "question_type": "text_input",
            "question_text": "As we conclude, what is one word or phrase that captures how you're feeling right now?",
            "placeholder": "Trust your first instinct...",
            "required": False
          }
        },
        {
          "index": 5,
          "block_type": "text",
          "config": {
            "style": "lead",
            "content": "May you carry the spirit of mindful awareness with you in all that you do. Your journey continues with each conscious breath and intentional choice."
          }
        }
      ]
    }
  ]
}

# 2) Demo: Mindful Morning --------------------------------------------
mindful_morning = {
  "activity": {"slug": "demo-mindful-morning", "status": "published"},
  "version": {
    "number": 1,
    "title": "Demo: Mindful Morning",
    "description": "A sample activity showcasing different block types",
    "is_published": True,
    "meta": {"demo": True}
  },
  "pages": [
    {
      "index": 0,
      "title": "Welcome",
      "meta": {"progress_label": "Introduction"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Welcome to Your Mindful Morning"}},
        {"index": 1, "block_type": "text", "config": {"style": "body", "content": "Take a moment to center yourself and begin this journey of mindfulness."}}
      ]
    },
    {
      "index": 1,
      "title": "Morning Reflection",
      "meta": {"progress_label": "Reflection"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h3", "content": "How are you feeling this morning?"}},
        {
          "index": 1,
          "block_type": "question",
          "config": {
            "question_id": "morning_feeling",
            "question_type": "multiple_choice",
            "question_text": "Select all that apply:",
            "required": True,
            "options": [
              {"value": "calm", "label": "Calm"},
              {"value": "energized", "label": "Energized"},
              {"value": "anxious", "label": "Anxious"},
              {"value": "tired", "label": "Tired"}
            ]
          }
        }
      ]
    }
  ]
}

# 3) Career exploration assessment ------------------------------------
career = {
  "activity": {"slug": "career-exploration-assessment", "status": "published"},
  "version": {
    "number": 1,
    "title": "Career Exploration Assessment",
    "description": "Discover your career interests and strengths",
    "is_published": True,
    "meta": {"demo": True, "category": "career"}
  },
  "pages": [
    {
      "index": 0,
      "title": "Career Discovery",
      "meta": {"progress_label": "Introduction"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Explore Your Career Path"}},
        {"index": 1, "block_type": "text", "config": {"style": "body", "content": "This assessment will help you discover career paths that align with your interests and strengths."}}
      ]
    },
    {
      "index": 1,
      "title": "Career Interests",
      "meta": {"progress_label": "Assessment"},
      "blocks": [
        {
          "index": 0,
          "block_type": "question",
          "config": {
            "question_id": "work_environment",
            "question_type": "single_choice",
            "question_text": "What type of work environment appeals to you most?",
            "options": [
              {"value": "collaborative", "label": "Collaborative team environment"},
              {"value": "independent", "label": "Independent, self-directed work"},
              {"value": "client_facing", "label": "Client-facing and relationship-building"},
              {"value": "creative", "label": "Creative and innovative projects"}
            ],
            "required": True
          }
        },
        {
          "index": 1,
          "block_type": "question",
          "config": {
            "question_id": "career_goals",
            "question_type": "text_input",
            "question_text": "Describe your ideal career in one sentence.",
            "placeholder": "My ideal career would be...",
            "multiline": True,
            "required": False
          }
        }
      ]
    }
  ]
}

# 4) Personal values discovery ----------------------------------------
values = {
  "activity": {"slug": "personal-values-discovery", "status": "published"},
  "version": {
    "number": 1,
    "title": "Personal Values Discovery",
    "description": "Identify and prioritize your core personal values",
    "is_published": True,
    "meta": {"demo": True, "category": "values"}
  },
  "pages": [
    {
      "index": 0,
      "title": "Values Exploration",
      "meta": {"progress_label": "Introduction"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Discover Your Core Values"}},
        {"index": 1, "block_type": "text", "config": {"style": "body", "content": "Understanding your personal values helps guide important life decisions and creates a foundation for authentic living."}}
      ]
    },
    {
      "index": 1,
      "title": "Value Priorities",
      "meta": {"progress_label": "Selection"},
      "blocks": [
        {
          "index": 0,
          "block_type": "question",
          "config": {
            "question_id": "top_values",
            "question_type": "multiple_choice",
            "question_text": "Select your top 5 most important values:",
            "options": [
              {"value": "authenticity", "label": "Authenticity"},
              {"value": "creativity", "label": "Creativity"},
              {"value": "family", "label": "Family"},
              {"value": "growth", "label": "Personal Growth"},
              {"value": "integrity", "label": "Integrity"},
              {"value": "freedom", "label": "Freedom"},
              {"value": "service", "label": "Service to Others"},
              {"value": "achievement", "label": "Achievement"},
              {"value": "balance", "label": "Work-Life Balance"},
              {"value": "adventure", "label": "Adventure"}
            ],
            "required": True,
            "multiple_selection": True
          }
        }
      ]
    }
  ]
}

# 5) Goal setting workshop --------------------------------------------
goals = {
  "activity": {"slug": "goal-setting-workshop", "status": "published"},
  "version": {
    "number": 1,
    "title": "Goal Setting Workshop",
    "description": "Learn to set and achieve meaningful personal goals",
    "is_published": True,
    "meta": {"demo": True, "category": "goals"}
  },
  "pages": [
    {
      "index": 0,
      "title": "Goal Setting Basics",
      "meta": {"progress_label": "Introduction"},
      "blocks": [
        {"index": 0, "block_type": "text", "config": {"style": "h2", "content": "Setting Meaningful Goals"}},
        {"index": 1, "block_type": "text", "config": {"style": "body", "content": "Effective goal setting combines clarity, motivation, and practical planning to help you achieve what matters most."}}
      ]
    },
    {
      "index": 1,
      "title": "Your Goals",
      "meta": {"progress_label": "Planning"},
      "blocks": [
        {
          "index": 0,
          "block_type": "question",
          "config": {
            "question_id": "primary_goal",
            "question_type": "text_input",
            "question_text": "What is one important goal you want to achieve in the next 6 months?",
            "placeholder": "Be specific and actionable...",
            "multiline": True,
            "required": True
          }
        },
        {
          "index": 1,
          "block_type": "question",
          "config": {
            "question_id": "goal_motivation",
            "question_type": "single_choice",
            "question_text": "What is your primary motivation for this goal?",
            "options": [
              {"value": "personal_growth", "label": "Personal growth and development"},
              {"value": "career_advancement", "label": "Career advancement"},
              {"value": "relationships", "label": "Improving relationships"},
              {"value": "health_wellness", "label": "Health and wellness"},
              {"value": "financial", "label": "Financial security"},
              {"value": "creative_expression", "label": "Creative expression"}
            ],
            "required": True
          }
        }
      ]
    }
  ]
}

paths = {
  "pathways-assessment.json": pathways,
  "demo-mindful-morning.json": mindful_morning,
  "career-exploration-assessment.json": career,
  "personal-values-discovery.json": values,
  "goal-setting-workshop.json": goals,
}

written = {fn: write_json(fn, data) for fn, data in paths.items()}
written