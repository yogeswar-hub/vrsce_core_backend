from com.dimcon.vrse_app.resources.vrse.vrse_audit_log import AuditLog
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class AuditLogService:
    @staticmethod
    def log_access(user_info, resource, http_method, location_id=None):
        try:
            # Determine action messages based on resource, etc.
            if resource == "club_users":
                action_map = {
                    "GET":    "User read club_ready members data.",
                    "PUT":    "User updated club_ready members data.",
                    "POST":   "User added new club_ready member.",
                    "DELETE": "User deleted club_ready members data."
                }
            elif resource == "platform_config":
                action_map = {
                    "GET":    "User read platform configuration.",
                    "PUT":    "User updated platform configuration.",
                    "POST":   "User created new platform configuration.",
                    "DELETE": "User deleted platform configuration."
                }
            elif resource == "club_locations":
                action_map = {
                    "GET":    "User read club locations data.",
                    "PUT":    "User updated club locations data.",
                    "POST":   "User added a new club location.",
                    "DELETE": "User deleted a club location."
                }
            elif resource == "audit_log":
                # Custom messages for audit log resource if needed.
                action_map = {
                    "GET":    "User viewed audit log history.",
                    "PUT":    "User updated an audit log entry.",    # if applicable
                    "POST":   "User created a new audit log entry.",  # if applicable
                    "DELETE": "User deleted an audit log entry."       # if applicable
                }
            else:
                action_map = {
                    "GET":    "User read data.",
                    "PUT":    "User updated data.",
                    "POST":   "User created a new record.",
                    "DELETE": "User deleted data."
                }
            
            engine = get_engine()
            db_util = DBSessionUtil(engine)
            with db_util.session_scope() as session:
                log_entry = AuditLog(
                    user_id  = user_info.get("user_id", "unknown"),
                    username = user_info.get("username", ""),
                    email    = user_info.get("email", ""),
                    resource = resource,
                    method   = http_method,
                    action   = action_map.get(http_method, "User performed an action")
                )
                if location_id:
                    log_entry.resource = f"{resource} (location: {location_id})"
                session.add(log_entry)
                session.commit()
                logger.info("Audit log created for user %s accessing %s with method %s%s",
                            user_info.get("user_id"),
                            resource,
                            http_method,
                            f" for location {location_id}" if location_id else "")
        except Exception as e:
            logger.error("Failed to log audit: %s", e, exc_info=True)

    @staticmethod
    def get_audit_logs(page=1, limit=20):
        try:
            engine = get_engine()
            db_util = DBSessionUtil(engine)
            with db_util.session_scope() as session:
                base_query = session.query(AuditLog).order_by(AuditLog.accessed_at.desc())
                total_count = base_query.count()
                logs = base_query.limit(limit).offset((page - 1) * limit).all()
                results = [log.to_dict() for log in logs]
                logger.info("Retrieved %s audit log records out of %s", len(results), total_count)
                return {"total_count": total_count, "results": results}
        except Exception as e:
            logger.error("Failed to retrieve audit logs: %s", e, exc_info=True)
            raise