# ================================
# Add project root to sys.path
# ================================
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# ================================
# Standard library imports
# ================================
from datetime import datetime

# ================================
# Third-party imports
# ================================
import pytz
from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, inspect
from sqlalchemy.orm import Session

# ================================
# Project-specific imports
# ================================
import logging
from com.dimcon.synthera.utilities.log_handler import LoggerManager
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil
from com.dimcon.synthera.resources.base import Base
from com.dimcon.synthera.resources.tasks.task import Task
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee

# ================================
# Model Definition
# ================================
class TasksCompleted(Base):
    __tablename__ = 'tasks_completed'

    completed_id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey(Task.task_id, ondelete="CASCADE"))
    completed_by = Column(Integer, ForeignKey(Employee.emp_id))
    completed_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    completion_notes = Column(Text)

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'tasks_completed' created.")
        else:
            logger.info("Table 'tasks_completed' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'tasks_completed' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        completed = cls(**kwargs)
        session.add(completed)
        session.commit()
        logger.info(f"Inserted completed task with ID: {completed.completed_id}")
        return completed

    @classmethod
    def update_table(cls, session: Session, completed_id: int, **kwargs):
        record = session.query(cls).filter_by(completed_id=completed_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()
            logger.info(f"Updated completed task record with ID: {completed_id}")
        else:
            logger.warning(f"Completed task with ID {completed_id} not found.")
        return record

    @classmethod
    def get_table(cls, session: Session, **filters):
        records = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(records)} completed task record(s) with filters: {filters}")
        return records

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # TasksCompleted.create_table(engine)
    # logger.info("TasksCompleted table creation complete.")

    # # Insert completed task
    new_completed = TasksCompleted.insert_table(
        session,
        task_id=1,
        completed_by=1,
        completion_notes="Task completed with all requirements met."
    )
    logger.info("TasksCompleted insertion complete.")

    # # Fetch completed tasks
    # completed = TasksCompleted.get_table(session, task_id=1)
    # logger.info(f"Fetched {len(completed)} completed tasks for task ID 1.")

    # # Update completed record
    # updated_completed = TasksCompleted.update_table(
    #     session,
    #     completed_id=new_completed.completed_id,
    #     completion_notes="Task completed after revision.",
    #     completed_by=2
    # )
    # if updated_completed:
    #     logger.info(f"Completed task ID {updated_completed.completed_id} updated successfully.")
    # else:
    #     logger.warning("Completed task not found. Cannot update.")

    # # Drop table
    # TasksCompleted.drop_table(engine)
    # logger.info("TasksCompleted table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. TasksCompleted script completed.")
