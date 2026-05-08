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
    

class ForexDB(Base):
    __tablename__ = "forex_data"
    
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(), primary_key=True)
    price_close: Mapped[float] = mapped_column(Float(), nullable=False)  
    

class TickerMeta(Base): 
    __tablename__ = "ticker_metadata"


    exchange = mapped_column(String())
    shortname  = mapped_column(String() )
    ticker = mapped_column(String(), primary_key = True )
    longname = mapped_column(String() )
    sector = mapped_column(String() )
    industry = mapped_column(String() )
    origin = mapped_column(String() )
    type  = mapped_column(String())
    currency  = mapped_column(String())
