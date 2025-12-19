from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, String, Float, create_engine
from datetime import datetime

class Base(DeclarativeBase):
    pass
