# ================================
# Add project root to sys.path
# ================================
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# ================================
# Standard library imports
# ================================
from datetime import datetime, timedelta
import calendar
import logging

# ================================
# Third-party imports
# ================================
import pytz
from sqlalchemy import Column, Integer, String, Date, Boolean, TIMESTAMP, inspect
from sqlalchemy.orm import Session

# ================================
# Project-specific imports
# ================================
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil
from com.dimcon.synthera.resources.base import Base

# ================================
# Model Definition
# ================================
class CalendarDates(Base):
    __tablename__ = 'calendar_dates'

    date = Column(Date, primary_key=True)
    year = Column(Integer)
    month = Column(Integer)
    day = Column(Integer)
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    day_name = Column(String(10))
    week_of_year = Column(Integer)
    quarter = Column(Integer)
    is_weekend = Column(Boolean)
    is_holiday = Column(Boolean, default=False)
    is_business_day = Column(Boolean)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'calendar_dates' created.")
        else:
            logger.info("Table 'calendar_dates' already exists. Skipping creation.")

    @classmethod
    def populate_dates(cls, session: Session, start_year=2024, end_year=2025):
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31)
        delta = timedelta(days=1)

        while start_date <= end_date:
            day_name = calendar.day_name[start_date.weekday()]
            day_of_week = start_date.weekday()
            is_weekend = day_of_week >= 5
            is_business_day = not is_weekend

            record = cls(
                date=start_date.date(),
                year=start_date.year,
                month=start_date.month,
                day=start_date.day,
                day_of_week=day_of_week,
                day_name=day_name,
                week_of_year=start_date.isocalendar()[1],
                quarter=(start_date.month - 1) // 3 + 1,
                is_weekend=is_weekend,
                is_business_day=is_business_day
            )
            session.merge(record)
            start_date += delta

        session.commit()
        logger.info(f"Calendar dates populated from {start_year} to {end_year}.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    engine = get_engine()
    db_util = DBSessionUtil(engine)

    CalendarDates.create_table(engine)

    # Use session_scope correctly
    with db_util.session_scope() as session:
        CalendarDates.populate_dates(session, start_year=2024, end_year=2025)

    logger.info("Session closed. Calendar dates script completed.")
