from com.dimcon.vrse_app.resources.vrse.vrse_audit_log import AuditLog
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class AuditLogService:
    @staticmethod
    def log_access(user_info, resource, http_method):
        try:
            engine = get_engine()
            db_util = DBSessionUtil(engine)
            with db_util.session_scope() as session:
                log_entry = AuditLog(
                    user_id=user_info.get("user_id", "unknown"),
                    username=user_info.get("username", ""),
                    resource=resource,
                    method=http_method
                )
                session.add(log_entry)
                session.commit()
                logger.info(f"Audit log created for user {user_info.get('user_id')} accessing {resource} with {http_method}.")
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")