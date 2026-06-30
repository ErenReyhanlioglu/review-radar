from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.review import Base


class ReviewAggregate(Base):
    __tablename__ = "review_aggregates"

    month: Mapped[date] = mapped_column(Date, primary_key=True)
    topic: Mapped[str] = mapped_column(String, primary_key=True)
    sentiment: Mapped[str] = mapped_column(String, primary_key=True)
    company_size: Mapped[str] = mapped_column(String, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
