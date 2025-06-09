from com.dimcon.vrse_app.resources.vrse.vrse_club_users import ClubUser
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

class ClubUserValidator:
    @staticmethod
    def validate_unique_users(session, unique_users: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
        """
        - If user_id exists AND email matches:
            - If all fields match: SKIP (already up to date)
            - If fields differ:    UPDATE
        - If user_id exists AND email differs: SKIP (log conflict)
        - If email exists but user_id differs: SKIP (log conflict)
        - Else: INSERT as new
        Returns: (to_upsert, conflicts, skipped)
        """
        uids   = [u["UserId"] for u in unique_users]
        emails = [u["Email"]  for u in unique_users]

        # Map of user_id → DB row as dict
        existing_by_uid = {str(r[0]): r[1] for r in
            session.query(ClubUser.user_id, ClubUser).filter(ClubUser.user_id.in_(uids)).all()
        }
        # Map of email → DB row as dict
        existing_by_email = {r[0]: r[1] for r in
            session.query(ClubUser.email, ClubUser).filter(ClubUser.email.in_(emails)).all()
        }

        to_upsert = []
        conflicts = []
        skipped = []

        # For comparing fields, define keys (adjust as needed)
        compare_fields = [
            "user_id", "email", "first_name", "last_name", "barcode", "username",
            "referral_type_id", "primary_store_id", "sub", "iss", "auth_time", "aud", "auth_time_human",
            "latest_segment", "latest_activity_date"
        ]

        for user in unique_users:
            uid   = str(user["UserId"])
            email = user["Email"]

            db_row_uid = existing_by_uid.get(uid)
            db_row_email = existing_by_email.get(email)

            # 1) user_id exists in DB
            if db_row_uid:
                db_email = db_row_uid.email
                if db_email != email:
                    logger.warning(
                        f"Skipping user_id {uid}: email mismatch (DB={db_email} vs Input={email})"
                    )
                    conflicts.append({
                        "type":    "user_id_email_mismatch",
                        "user":    user,
                        "db_email": db_email
                    })
                    continue

                # Same user_id and email, check if data actually changed
                db_dict = db_row_uid.to_dict()
                needs_update = False
                for k in compare_fields:
                    # DB stores user_id as int, incoming as string sometimes
                    v_db = str(db_dict[k]) if k == "user_id" else db_dict.get(k)
                    v_in = str(user["UserId"]) if k == "user_id" else user.get(ClubUserValidator.camel_to_snake(k), None)
                    if v_db != v_in:
                        needs_update = True
                        break

                if needs_update:
                    to_upsert.append(user)
                    logger.info(f"Will update user_id={uid}, email={email}")
                else:
                    skipped.append(user)
                    logger.info(f"No change for user_id={uid}, email={email} (skipped)")
                continue

            # 2) email exists but user_id does not
            if db_row_email:
                db_uid = db_row_email.user_id
                if str(db_uid) != uid:
                    logger.warning(
                        f"Skipping email {email}: user_id mismatch (DB={db_uid} vs Input={uid})"
                    )
                    conflicts.append({
                        "type":    "email_user_id_mismatch",
                        "user":    user,
                        "db_user_id": db_uid
                    })
                    continue

            # 3) Otherwise, this is new or a legit update
            to_upsert.append(user)

        logger.info(
            "Validation complete: will upsert %d users; skipped %d already up-to-date; %d conflicts",
            len(to_upsert), len(skipped), len(conflicts)
        )
        return to_upsert, conflicts, skipped

    @staticmethod
    def camel_to_snake(name):
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
