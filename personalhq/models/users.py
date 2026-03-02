"""Module defining SQLAlchemy model of Users."""

from datetime import datetime, date

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db, bcrypt


class User(UserMixin, db.Model):
    """Class representing table Users in database."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    last_login: Mapped[datetime | None]
    date_of_birth: Mapped[date | None]
    life_expectancy: Mapped[int | None]

    subscriptions = relationship("Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    habits = relationship("Habit", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    time_buckets = relationship("TimeBucket",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    tasks = relationship("Task",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    brain_dumps = relationship("BrainDump",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    focus_sessions = relationship("FocusSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    identities = relationship("Identity",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    journals = relationship("Journal",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def check_password(self, password: str) -> bool:
        """Verifies if the provided plain-text password matches the hash."""
        return bcrypt.check_password_hash(self.password, password)

    def __init__(self, email: str,
                 first_name: str,
                 last_name: str,
                 password: str):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.last_login = datetime.now()
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def __repr__(self):
        return (
            f'<User {self.id} - {self.first_name} {self.last_name}>'
            f' {self.email}'
            f' {self.last_login}'
        )
