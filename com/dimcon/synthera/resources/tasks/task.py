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
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, inspect
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
from com.dimcon.synthera.resources.tasks.task_status import TaskStatus
from com.dimcon.synthera.resources.tasks.task_priority import TaskPriority
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee
from com.dimcon.synthera.resources.leads.leads_details import LeadDetail

# ================================
# Model Definition
# ================================
class Task(Base):
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    task_title = Column(String(255), nullable=False)
    task_description = Column(Text)
    status_id = Column(Integer, ForeignKey(TaskStatus.status_id))
    priority_id = Column(Integer, ForeignKey(TaskPriority.priority_id))
    assigned_to = Column(Integer, ForeignKey(Employee.emp_id))
    lead_id = Column(Integer, ForeignKey(LeadDetail.lead_id))
    due_date = Column(TIMESTAMP(timezone=True))
    created_by = Column(Integer, ForeignKey(Employee.emp_id))
    updated_by = Column(Integer, ForeignKey(Employee.emp_id))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc))
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.now(pytz.utc), onupdate=datetime.now(pytz.utc))

    @classmethod
    def create_table(cls, engine):
        inspector = inspect(engine)
        if cls.__tablename__ not in inspector.get_table_names():
            cls.__table__.create(bind=engine)
            logger.info("Table 'tasks' created.")
        else:
            logger.info("Table 'tasks' already exists. Skipping creation.")

    @classmethod
    def drop_table(cls, engine):
        cls.__table__.drop(bind=engine, checkfirst=True)
        logger.info("Table 'tasks' dropped.")

    @classmethod
    def insert_table(cls, session: Session, **kwargs):
        new_task = cls(**kwargs)
        session.add(new_task)
        session.commit()
        logger.info(f"Inserted task with ID: {new_task.task_id}")
        return new_task

    @classmethod
    def update_table(cls, session: Session, task_id: int, **kwargs):
        task = session.query(cls).filter_by(task_id=task_id).first()
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            session.commit()
            logger.info(f"Updated task with ID: {task_id}")
        else:
            logger.warning(f"Task with ID {task_id} not found.")
        return task

    @classmethod
    def get_table(cls, session: Session, **filters):
        tasks = session.query(cls).filter_by(**filters).all()
        logger.info(f"Fetched {len(tasks)} task(s) with filters: {filters}")
        return tasks

    @classmethod
    def alter_table(cls):
        raise NotImplementedError("Use Alembic or raw SQL for altering tables.")

# ================================
# Main Script Execution
# ================================
if __name__ == "__main__":
    # # Create table
    # Task.create_table(engine)
    # logger.info("Tasks table creation complete.")

    # # Insert task
    new_task = Task.insert_table(
        session,
        task_title="Prepare Sales Report",
        task_description="Generate Q2 sales performance report.",
        status_id=1,
        priority_id=1,
        assigned_to=1,
        lead_id=1,
        due_date=datetime(2025, 5, 1, 12, 0, tzinfo=pytz.utc),
        created_by=1,
        updated_by=1
    )
    logger.info("Task insertion into tasks table complete.")

    # # Fetch tasks
    # tasks = Task.get_table(session, assigned_to=1)
    # logger.info(f"Fetched {len(tasks)} tasks assigned to employee 1.")

    # # Update task
    # updated_task = Task.update_table(
    #     session,
    #     task_id=new_task.task_id,
    #     task_description="Include graphs and summaries",
    #     updated_by=2
    # )
    # if updated_task:
    #     logger.info(f"Task ID {updated_task.task_id} updated successfully.")
    # else:
    #     logger.warning("Task not found. Cannot update.")

    # # Drop table
    # Task.drop_table(engine)
    # logger.info("Tasks table dropped.")

    # Close session
    session.close()
    logger.info("Session closed. Tasks script completed.")
