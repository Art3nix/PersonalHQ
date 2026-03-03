"""Module handling the business logic for Journals."""

import random
from personalhq.models.journals import JournalFrequency
from personalhq.services.time_service import get_local_today

def get_active_prompt(journal):
    """
    Determines which JournalPrompt to display based on the journal's 
    rotation frequency and the current date.
    """
    if not journal.prompts: #
        return None

    count = len(journal.prompts)
    today = get_local_today()

    # Calculate a deterministic index based on the frequency
    if journal.frequency == JournalFrequency.DAILY:
        # toordinal() returns an integer representing the day since Jan 1, 1 AD
        index = today.toordinal() % count

    elif journal.frequency == JournalFrequency.WEEKLY:
        # isocalendar()[1] returns the current week number of the year
        index = today.isocalendar()[1] % count

    elif journal.frequency == JournalFrequency.MONTHLY:
        # Create an absolute month integer to ensure smooth year-over-year rollover
        absolute_month = (today.year * 12) + today.month
        index = absolute_month % count

    elif journal.frequency == JournalFrequency.YEARLY:
        index = today.year % count

    elif journal.frequency == JournalFrequency.ON_DEMAND:
        # Pick a new random prompt every single time the page loads
        index = random.randint(0, count - 1)

    else:
        index = 0

    # Return the specific JournalPrompt model
    return journal.prompts[index]
