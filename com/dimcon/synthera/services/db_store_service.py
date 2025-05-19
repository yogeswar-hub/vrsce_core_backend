import logging
from com.dimcon.synthera.utilities.log_handler import LoggerManager
from com.dimcon.synthera.resources.statement_of_work.sow_mapping_table import MeetingQAS
from com.dimcon.synthera.resources.meeting.meeting import Meeting
from com.dimcon.synthera.resources.leads.leads_details import LeadDetail
from com.dimcon.synthera.resources.organization_and_employees.employees import Employee
from com.dimcon.synthera.resources.organization_and_employees.organization import Organization
from com.dimcon.synthera.resources.connect_aurora import get_engine
from com.dimcon.synthera.utilities.sessions_manager import DBSessionUtil

# Setup logger
logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

# Initialize DB engine and session utility
engine = get_engine()
db_util = DBSessionUtil(engine)

class SOWDataService:
    @classmethod
    def store_data(cls, parsed_data: dict) -> bool:
        """
        Store extracted Q&A data into the meeting_qas table using metadata from related tables.

        Parameters:
            parsed_data (dict): Contains 'meeting_id' and 'answers' (a list of Q&A dictionaries).

        Returns:
            bool: True if data is inserted successfully, False if any required step fails.
        """
        try:
            # Extract meeting ID and Q&A list from parsed input
            event_meeting_id = parsed_data.get("meeting_id")
            qa_list = parsed_data.get("answers", [])

            if not event_meeting_id or not qa_list:
                logger.error("Parsed data is missing 'meeting_id' or 'answers'.")
                return False

            # Open a database session
            with db_util.session_scope() as session:
                # Fetch meeting by ID
                meeting = session.query(Meeting).filter_by(meeting_id=event_meeting_id).first()
                if not meeting:
                    logger.error(f"No meeting found for meeting_id: {event_meeting_id}")
                    return False

                # Get lead using meeting.lead_id
                lead = session.query(LeadDetail).filter_by(lead_id=meeting.lead_id).first()

                # Get employee who created the meeting (creator)
                employee = session.query(Employee).filter_by(emp_id=meeting.created_by).first()

                # Get organization using employee.organization_id
                organization = None
                if employee and employee.organization_id:
                    organization = session.query(Organization).filter_by(
                        organization_id=employee.organization_id
                    ).first()

                if not lead or not employee:
                    logger.error("Missing lead or employee for meeting_id: %s", event_meeting_id)
                    return False

                # Format lead full name
                lead_name = f"{(lead.lead_first_name or '').strip()} {(lead.lead_last_name or '').strip()}".strip()

                # Insert each question-answer pair into the meeting_qas table
                for qa in qa_list:
                    MeetingQAS.insert_table(
                        meeting_id=meeting.meeting_id,
                        meeting_title=meeting.meeting_title,
                        lead_id=lead.lead_id,
                        lead_name=lead_name,
                        emp_id=employee.emp_id,
                        emp_name=employee.employee_name,
                        org_id=organization.organization_id if organization else None,
                        organization_name=organization.organization_name if organization else "Unknown",
                        question_number=qa.get("question_number"),
                        question_text=qa.get("question_text"),
                        answer_text=qa.get("answer_text")
                    )

                logger.info("Inserted %d Q&A rows for meeting_id=%s", len(qa_list), event_meeting_id)
                return True

        except Exception as e:
            logger.error("Error in SOWDataService.store_data: %s", str(e), exc_info=True)
            return False
