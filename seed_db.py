"""Script to seed the Personal HQ database with test data."""

import random
from datetime import datetime, timedelta, date
from sqlalchemy.exc import IntegrityError

from personalhq import create_app
from personalhq.extensions import db
from personalhq.models.users import User
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.models.tasks import Task
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.experiences import Experience
from personalhq.models.bucket_experience import BucketExperience
from personalhq.models.coretheme import CoreTheme
from personalhq.models.emotionalvalue import EmotionalValue
from personalhq.models.focussessions import FocusSession, SessionStatus

def run_seed():
    """Generates a test user and populates the dashboard with dummy data."""
    app = create_app()

    with app.app_context():
        print("Starting database seed...")

        # 1. Create the Test User
        # Uses the custom __init__ from users.py which hashes the password automatically
        test_user = User(
            email="jacob@example.com",
            first_name="Jacob",
            last_name="Workspace",
            password="password123"
        )
        test_user.date_of_birth = date(1996, 5, 15)
        test_user.life_expectancy = 82

        db.session.add(test_user)

        try:
            db.session.commit()
            print("Created user: jacob@example.com (Password: password123)")
        except IntegrityError:
            db.session.rollback()
            test_user = User.query.filter_by(email="jacob@example.com").first()
            print("User already exists, skipping creation.")

        user_id = test_user.id
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        # 2. Clear existing habits/tasks for a clean slate (optional, but good for testing)
        Habit.query.filter_by(user_id=user_id).delete()
        Task.query.filter_by(user_id=user_id).delete()
        BucketExperience.query.delete()
        # If you created TagExperience, uncomment the line below:
        # TagExperience.query.delete()
        TimeBucket.query.filter_by(user_id=user_id).delete()
        Experience.query.delete()
        CoreTheme.query.delete()
        EmotionalValue.query.delete()
        FocusSession.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        # 3. Create Dummy Habits
        habits = [
            Habit(
                user_id=user_id,
                name="Daily 5km Run",
                identity="Athlete Identity",
                icon="🏃‍♂️",
                frequency=HabitFrequency.DAILY,
                streak=12,
                category="Health",
                last_completed=yesterday # Ready to be checked today
            ),
            Habit(
                user_id=user_id,
                name="Morning Review",
                identity="Planner Identity",
                icon="📓",
                frequency=HabitFrequency.DAILY,
                streak=45,
                category="Mindset",
                last_completed=now # Already checked today to test the UI state
            ),
            Habit(
                user_id=user_id,
                name="Weekly Finance Sync",
                identity="Wealth Builder",
                icon="💰",
                frequency=HabitFrequency.WEEKLY,
                streak=4,
                category="Finance",
                last_completed=now - timedelta(days=3) # Completed a few days ago
            )
        ]
        db.session.add_all(habits)
        # HabitLogs
        seeded_habits = Habit.query.filter_by(user_id=user_id).all()

        logs_to_add = []
        today = date.today()

        # 3. Loop backwards through the last 30 days
        for i in range(30):
            current_date = today - timedelta(days=i)

            for habit in seeded_habits:
                # Give it a 70% chance of being completed on any given day
                if random.random() < 0.70:
                    logs_to_add.append(
                        HabitLog(
                            habit_id=habit.id,
                            completed_date=current_date,
                            # Fake the exact timestamp to noon on that day
                            logged_at=datetime.combine(current_date, datetime.strptime('12:00:00', '%H:%M:%S').time()) 
                        )
                    )

                    # If the date is today, and we completed it, update the parent habit's last_completed
                    if i == 0:
                        habit.last_completed = current_date

        db.session.add_all(logs_to_add)

        # 4. Create Dummy Tasks (to populate the bottom right GTD list)
        tasks = [
            Task(
                user_id=user_id,
                title_name="Journal Morning Thoughts",
                is_completed=False,
                created_at=now
            ),
            Task(
                user_id=user_id,
                title_name="Meditate - try 15 mins",
                is_completed=False,
                created_at=now
            )
        ]
        db.session.add_all(tasks)

        # 5. Create a Time Bucket
        bucket_30s = TimeBucket(
            user_id=user_id,
            name="My 30s",
            theme="Wealth Building & Adventure",
            start_date=date(2026, 1, 1), # Adjust to your actual time bucket dates
            end_date=date(2035, 12, 31)
        )
        db.session.add(bucket_30s)
        db.session.flush() # Flush to get the bucket_30s.id

        # Create Categories
        theme_adventure = CoreTheme(name="Adventure & Travel")
        theme_growth = CoreTheme(name="Personal Growth")
        val_awe = EmotionalValue(name="Awe & Wonder")
        db.session.add_all([theme_adventure, theme_growth, val_awe])
        db.session.flush()

        # Create an Experience (Assuming theme/emotional_values are commented out or created)
        japan_trip = Experience(
            name="Ski in Niseko, Japan",
            details="2-week powder skiing trip with friends.",
            theme_id=theme_adventure.id,
            emotional_value_id=val_awe.id
        )
        db.session.add(japan_trip)
        db.session.flush()

        # Link them together
        link = BucketExperience(bucket_id=bucket_30s.id, experience_id=japan_trip.id)
        db.session.add(link)

        # 6. Create Planned Focus Sessions for Today
        sessions = [
            FocusSession(
                user_id=user_id,
                name="Create MVP API Schema",
                target_date=now.date(),
                target_duration_minutes=90,
                status=SessionStatus.NOT_STARTED,
                queue_order=1,
                start_time=None,
                total_paused_seconds=0,
                last_paused_tick=now
            ),
            FocusSession(
                user_id=user_id,
                name="Write Documentation",
                target_date=now.date(),
                target_duration_minutes=45,
                status=SessionStatus.NOT_STARTED,
                queue_order=2,
                start_time=None,
                total_paused_seconds=0,
                last_paused_tick=now
            ),
            FocusSession(
                user_id=user_id,
                name="Inbox Zero & Admin",
                target_date=now.date(),
                target_duration_minutes=30,
                status=SessionStatus.NOT_STARTED,
                queue_order=3,
                start_time=None,
                total_paused_seconds=0,
                last_paused_tick=now
            )
        ]
        db.session.add_all(sessions)
        db.session.commit()

        # Commit everything
        db.session.commit()
        print("Successfully seeded habits, tasks, and time buckets!")

if __name__ == "__main__":
    run_seed()
