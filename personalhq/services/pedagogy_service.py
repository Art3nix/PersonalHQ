"""Service layer for managing pedagogical content and knowledge base."""

from enum import Enum
from personalhq.extensions import db


class KnowledgeCategory(Enum):
    """Categories of knowledge content."""
    HABITS = "habits"
    IDENTITY = "identity"
    DEEP_WORK = "deep_work"
    TIME_BUCKETS = "time_buckets"
    GTD = "gtd"
    GENERAL = "general"


# Default knowledge base - can be extended by admins
DEFAULT_KNOWLEDGE_BASE = {
    "habits": {
        "title": "Building Habits",
        "description": "Learn how to build lasting habits that reinforce your identity.",
        "content": """
## The Science of Habits

Habits are the compound interest of self-improvement. Small, consistent actions lead to remarkable results.

### Key Principles:
- **Identity-Based Habits**: Focus on who you want to become, not what you want to achieve
- **The Habit Loop**: Cue → Craving → Response → Reward
- **Streaks Matter**: Consistency is more important than intensity
- **Two-Day Rule**: Missing once is a slip, missing twice is the start of a new habit

### How to Use PersonalHQ:
1. Define your identity (e.g., "I am someone who writes daily")
2. Create habits that reinforce that identity
3. Track daily to build proof of your identity
4. Watch your streak grow as evidence of who you are

*Reference: Atomic Habits by James Clear*
        """
    },
    "identity": {
        "title": "Identity-Based Change",
        "description": "Understand how to use identity to drive lasting behavior change.",
        "content": """
## Identity-Based Habits

The most effective way to change behavior is to focus on who you wish to become, not the outcomes you want.

### The Identity Shift:
- **Outcome-Based**: "I want to run a marathon" → Often fails
- **Identity-Based**: "I am a runner" → Sustainable

### Building Your Identities:
1. Choose identities that matter to you (e.g., "The Writer", "The Athlete", "The Builder")
2. Attach habits to each identity
3. Every completed habit is a "vote" for that identity
4. Over time, your identity becomes real through consistent action

### In PersonalHQ:
- Create identities that represent who you want to become
- Assign habits to identities to reinforce them
- Track progress and see your identity strengthen

*Reference: Atomic Habits by James Clear, Man's Search for Meaning by Viktor Frankl*
        """
    },
    "deep_work": {
        "title": "Deep Work & Focus",
        "description": "Master the art of undistracted, high-value work.",
        "content": """
## Deep Work

Deep work is professional activity performed in a state of undistracted concentration that pushes your cognitive abilities to their limit.

### Why Deep Work Matters:
- Most valuable work requires deep focus
- Shallow work is easy to do but hard to improve
- Deep work is rare and therefore valuable

### The PersonalHQ Approach:
1. **Schedule Deep Work**: Plan your focus sessions in advance
2. **Protect Your Time**: Use the focus timer to eliminate distractions
3. **Track Progress**: Build evidence of your deep work capacity
4. **Reflect**: Review what you accomplished

### Best Practices:
- Start with 50-90 minute sessions
- Eliminate all notifications and distractions
- Have a clear intention before starting
- Track your progress over time

*Reference: Deep Work by Cal Newport*
        """
    },
    "time_buckets": {
        "title": "Life Planning with Time Buckets",
        "description": "Plan your life in decades and make intentional choices.",
        "content": """
## Die With Zero: Time Buckets

Life is finite. By dividing your life into decades, you can make intentional choices about how to spend your time.

### The Concept:
- Divide your life into 5-10 year periods
- For each period, define what experiences matter most
- Prioritize experiences while you have the health and time to enjoy them
- Avoid regret by being intentional

### Using Time Buckets in PersonalHQ:
1. Create time buckets for each life phase (e.g., "25-35: Build Career & Travel")
2. Add experiences you want to fulfill in that period
3. Track progress as you complete them
4. Move to the next bucket when the time comes

### Why This Matters:
- Forces you to think long-term
- Prevents the "I'll do it later" trap
- Creates urgency and motivation
- Helps you live intentionally

*Reference: Die With Zero by Bill Perkins*
        """
    },
    "gtd": {
        "title": "Getting Things Done (GTD)",
        "description": "Capture your thoughts and convert them into actionable tasks.",
        "content": """
## Getting Things Done

GTD is a method for capturing, organizing, and executing on all your ideas and tasks.

### The Five Steps:
1. **Capture**: Write down everything on your mind (inbox)
2. **Clarify**: Decide what each item means and what to do about it
3. **Organize**: Put items in the right categories
4. **Reflect**: Review regularly to stay on top of things
5. **Engage**: Do the work

### In PersonalHQ:
- Use the **Brain Dump** to capture all thoughts
- Convert ideas into habits, deep work sessions, or journal entries
- Keep your mind clear by externalizing everything
- Review daily to stay organized

### Benefits:
- Reduces mental load
- Ensures nothing falls through the cracks
- Frees your mind for creative work

*Reference: Getting Things Done by David Allen*
        """
    },
    "general": {
        "title": "PersonalHQ Fundamentals",
        "description": "Get started with PersonalHQ and understand the system.",
        "content": """
## Welcome to PersonalHQ

PersonalHQ is a productivity system designed to help you build the life you want through intentional habits, deep work, and life planning.

### Core Concepts:
- **Identities**: Who you want to become
- **Habits**: Small actions that reinforce your identity
- **Deep Work**: Undistracted focus on high-value tasks
- **Time Buckets**: Long-term life planning
- **Brain Dump**: Capture all your thoughts

### Getting Started:
1. Define 2-3 identities that matter to you
2. Create 3-5 habits that reinforce those identities
3. Start tracking daily
4. Add deep work sessions to your calendar
5. Plan your life in time buckets

### The Philosophy:
PersonalHQ is built on the principle that **small, consistent actions compound over time**. By focusing on your identity and taking daily actions that reinforce it, you become the person you want to be.

### Remember:
- Nobody is perfect. Missing once is a slip, missing twice is a new habit.
- Consistency matters more than intensity.
- Your identity is built through daily action.
- You have the power to design your life.

*Let's build something great together.*
        """
    }
}


def get_knowledge_content(category: str = None) -> dict:
    """
    Retrieve knowledge base content.
    If category is specified, return that category.
    Otherwise, return all categories.
    """
    if category and category in DEFAULT_KNOWLEDGE_BASE:
        return DEFAULT_KNOWLEDGE_BASE[category]
    
    return DEFAULT_KNOWLEDGE_BASE


def get_knowledge_by_category(category: str) -> dict:
    """Get knowledge content for a specific category."""
    if category not in DEFAULT_KNOWLEDGE_BASE:
        return {"error": "Category not found"}
    
    return DEFAULT_KNOWLEDGE_BASE[category]


def add_custom_knowledge(category: str, title: str, content: str) -> dict:
    """
    Add custom knowledge content (admin function).
    In production, this would be stored in the database.
    """
    # TODO: Implement database storage for custom knowledge
    return {
        "status": "success",
        "message": "Custom knowledge added (feature coming soon)"
    }


def get_pedagogy_modal_data() -> dict:
    """
    Get all pedagogy data formatted for the modal UI.
    Returns categories and their content.
    """
    categories = []
    for key, value in DEFAULT_KNOWLEDGE_BASE.items():
        categories.append({
            "id": key,
            "title": value["title"],
            "description": value["description"]
        })
    
    return {
        "categories": categories,
        "content": DEFAULT_KNOWLEDGE_BASE
    }
