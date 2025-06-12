from sqlalchemy import func
from dateutil import parser
from datetime import datetime, timedelta   # add timedelta
from com.dimcon.vrse_app.resources.vrse.vrse_audit_log import AuditLog
from com.dimcon.vrse_app.resources.connect_aurora import get_engine
from com.dimcon.vrse_app.utilities.sessions_manager import DBSessionUtil
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class AuditLogService:
    @staticmethod
    def log_access(user_info, resource, http_method, location_id=None, error_message: str=None):
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
            elif resource == "club_ready_sync":
                action_map = {
                    "SCHEDULE":              "System scheduled ClubReady sync via EventBridge.",
                    "SYNC_LOCATIONS":        "System synced club locations.",
                    "FETCH_SEGMENT_USERS":   "System fetched segmented users.",
                    "INSERT_SEGMENT_USERS":  "System inserted segmented users.",
                    "SYNC_ALL_USERS":        "System ran full user sync (dedupe & upsert).",
                    "UPDATE_LATEST_ACTIVITY":"System updated latest activity info.",
                    "POST":                  "System ran ClubReady sync."  # keep as fallback if needed
                }
            else:
                action_map = {
                    "GET":    "System performed data retrieval.",
                    "PUT":    "System updated data.",
                    "POST":   "System created a new record.",
                    "DELETE": "System deleted data."
                }
            action = action_map.get(http_method, "System performed an action")
            if error_message:
                action = f"{action} Error: {error_message}"
            
            engine = get_engine()
            db_util = DBSessionUtil(engine)
            with db_util.session_scope() as session:
                log_entry = AuditLog(
                    user_id  = user_info.get("user_id", "unknown"),
                    username = user_info.get("username", ""),
                    email    = user_info.get("email", ""),
                    resource = resource,
                    method   = http_method,
                    action   = action
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
    def get_audit_logs(page=1, limit=20, search=None, start_date=None, end_date=None):
        """
        Retrieve audit logs with optional search filtering and date range filtering.
          - search: a string to search in resource, action, or username fields (case-insensitive)
          - start_date: filter logs with accessed_at >= start_date (parseable format, e.g., "06-06-2025")
          - end_date:   filter logs with accessed_at <= end_date (same as above)
        """
        try:
            # --- parse dates ------------------------------------------------
            if start_date:
                try:
                    start_date = parser.parse(start_date)
                except Exception as e:
                    logger.error("Failed to parse start_date '%s': %s", start_date, e)
                    start_date = None
            if end_date:
                try:
                    # parse string → midnight of that day
                    end_date = parser.parse(end_date)
                    # bump to next day so "< end_date" includes full 06-11-2025
                    end_date = end_date + timedelta(days=1)
                except Exception as e:
                    logger.error("Failed to parse end_date '%s': %s", end_date, e)
                    end_date = None
            # ------------------------------------------------------------------

            # ----  pagination -----------------------------------------
            page   = max(1, int(page))      
            limit  = max(1, int(limit))    
            offset = (page - 1) * limit
            # ------------------------------------------------------------------

            engine = get_engine()
            db_util = DBSessionUtil(engine)
            with db_util.session_scope() as session:
                base_query = session.query(AuditLog)

                # Exclude generic health-check or system pings:
                # remove entries where user_id is 'unknown' and both email & username are empty/null
                base_query = base_query.filter(
                    ~(
                        (AuditLog.user_id == "unknown")
                        & ((AuditLog.username == None) | (AuditLog.username == ""))
                        & ((AuditLog.email    == None) | (AuditLog.email    == ""))
                    )
                )

                if search:
                    term = f"%{search.lower()}%"
                    base_query = base_query.filter(
                        func.lower(AuditLog.resource).like(term) |
                        func.lower(AuditLog.action).like(term)   |
                        func.lower(AuditLog.username).like(term)
                    )

                if start_date:
                    base_query = base_query.filter(AuditLog.accessed_at >= start_date)
                if end_date:
                    # now we use < end_date (which is start of day+1)
                    base_query = base_query.filter(AuditLog.accessed_at < end_date)

                base_query = base_query.order_by(AuditLog.accessed_at.desc())
                total_count = base_query.count()

                logs = base_query.limit(limit).offset(offset).all()
                results = [log.to_dict() for log in logs]

                logger.info(
                    "Retrieved %s audit log record(s) out of %s (page=%s, limit=%s)", 
                    len(results), total_count, page, limit
                )
                # include paging info alongside total_count and results
                return {
                    "page":        page,
                    "limit":       limit,
                    "total_count": total_count,
                    "results":     results
                }

        except Exception as e:
            logger.error("Failed to retrieve audit logs: %s", e, exc_info=True)
            raise