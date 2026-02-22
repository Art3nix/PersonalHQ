"""Module defining SQLAlchemy model of Plans."""

from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db


class Plan(db.Model):  # pylint: disable=R0902,R0903; # sqlalchemy class used to only store data
    """Class representing table Plans in database."""
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)
    access_level: Mapped[int] = mapped_column(nullable=False)

    subscriptions = relationship(
        "Subscription",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __init__(
        self,
        name: str,
        price: int,
        access_level: int
    ):  # pylint: disable=R0913; # related to previous warnings
        self.name = name
        self.price = price
        self.access_level = access_level

    def __repr__(self):
        return (
            f'<Plan {self.id} - {self.name}>'
            f' {self.price}CZK'
            f' access level: {self.access_level}'
        )
