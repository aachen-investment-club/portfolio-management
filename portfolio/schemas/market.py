from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, String, Float
from datetime import datetime


class Base(DeclarativeBase):
    pass


class MarketDB(Base):
    __tablename__ = "portfolio_management_developer"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(), primary_key=True)
    price_close: Mapped[float] = mapped_column(Float(), nullable=False)
