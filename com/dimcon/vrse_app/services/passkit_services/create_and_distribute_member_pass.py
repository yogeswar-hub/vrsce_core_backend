import grpc
from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp
from passkit_io.member import member_pb2, a_rpc_pb2_grpc
from passkit_io.common import personal_pb2, distribution_pb2
from passkit_io.core.a_rpc_distribution_pb2_grpc import DistributionStub
from com.dimcon.vrse_app.utilities.grpc_client import GrpcClient
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")


class CreateandDistributeMemberPass:
    """Manage PassKit members: create, update, send welcome emails via gRPC."""

    def _init_(self):
        self.program_id = "28waGT2C2wCJOOjqmSmL8J"
        self.grpc_client = GrpcClient()
        self.stub = self.grpc_client.get_members_stub()
        self.dist_stub = DistributionStub(self.grpc_client.get_channel())
        logger.info("Initialized CreateandDistributeMemberPass with gRPC stubs.")

    def get_member_by_external_id(self, external_id: str):
        request = member_pb2.MemberRecordByExternalIdRequest(
            externalId=external_id,
            programId=self.program_id
        )
        logger.debug(f"Fetching member with externalId={external_id}")
        return self.stub.getMemberRecordByExternalId(request)

    def create_member(self, user_data: dict):
        external_id = str(user_data.get("user_id"))
        tier_id = user_data.get("tier_id", "membership")
        profile_image_url = user_data.get("profile_image_url")
        expiry_date_str = user_data.get("expiry_date")

        if not expiry_date_str:
            logger.warning(f"User {external_id} skipped: No expiry date provided.")
            return None  # skip creating member

        expiry = Timestamp()
        try:
            expiry_dt = datetime.strptime(expiry_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            expiry.FromDatetime(expiry_dt)
        except Exception as e:
            logger.warning(f"User {external_id} skipped: Invalid expiry date format. Error: {e}")
            return None

        person = personal_pb2.Person(
            forename=user_data.get("first_name", "Unknown"),
            surname=user_data.get("last_name", "Unknown"),
            emailAddress=user_data.get("email", ""),
            mobileNumber=user_data.get("mobile_phone", "")
        )

        member = member_pb2.Member(
            externalId=external_id,
            programId=self.program_id,
            tierId=tier_id,
            person=person,
            metaData={"source": "auto-import"},
            status=0,
            expiryDate=expiry,
        )

        if profile_image_url:
            member.profileImage = profile_image_url

        logger.info(f"Creating new member with externalId={external_id}")
        response = self.stub.enrolMember(member)
        logger.info(f"Created new member with id={response.id}")
        return response

    def update_member(self, member_id: str, user_data: dict):
        person = personal_pb2.Person(
            forename=user_data.get("first_name", "Unknown"),
            surname=user_data.get("last_name", "Unknown"),
            emailAddress=user_data.get("email", ""),
            mobileNumber=user_data.get("mobile_phone", "")
        )
        member_update = member_pb2.Member(id=member_id, person=person)
        logger.info(f"Updating member id={member_id}")
        self.stub.updateMember(member_update)
        logger.info(f"Updated member id={member_id}")

    def send_welcome_email(self, member):
        request = distribution_pb2.EmailDistributionRequest(
            id=member.id,
            classId=member.programId,
            externalId=member.externalId,
            protocol=100,
            alternativeEmail=member.person.emailAddress
        )
        logger.info(f"Sending welcome email to {member.person.emailAddress}")
        self.dist_stub.sendWelcomeEmail(request)
        logger.info(f"Welcome email sent to {member.person.emailAddress}")
        return True

    def process_user(self, user_data: dict):
        external_id = str(user_data.get("user_id"))
        user_created = False
        user_updated = False

        try:
            logger.info(f"Checking if member exists for externalId={external_id}")
            member = self.get_member_by_external_id(external_id)
            logger.info("Member exists; verifying data for updates.")

            current = member.person
            needs_update = (
                current.forename != user_data.get("first_name") or
                current.surname != user_data.get("last_name") or
                current.emailAddress != user_data.get("email") or
                current.mobileNumber != user_data.get("mobile_phone")
            )
            if needs_update:
                logger.info("Member data differs; updating member.")
                self.update_member(member.id, user_data)
                member = self.get_member_by_external_id(external_id)
                user_updated = True

        except grpc.RpcError as e:
            if e.code().name == "NOT_FOUND":
                logger.info("Member not found; attempting to create new member.")
                member = self.create_member(user_data)
                if not member:
                    return {
                        "status": "skipped",
                        "message": "Missing or invalid expiry date. Pass not created."
                    }
                member = self.get_member_by_external_id(external_id)
                user_created = True
            else:
                logger.error(f"gRPC error {e.code().name}: {e.details()}", exc_info=True)
                return {"status": "error", "message": f"{e.code().name}: {e.details()}"}

        email_sent = self.send_welcome_email(member)

        if user_created:
            message = "User created and pass distributed."
        elif user_updated:
            message = "User information updated and pass distributed."
        else:
            message = "User already existed; pass distributed again."

        return {
            "status": "success",
            "member_id": member.id,
            "email_sent": email_sent,
            "message": message
        }

if __name__ == "__main__":
    sample_user = {
        "user_id": "12345",
        "first_name": "kkn",
        "last_name": "Doe",
        "email": "avirneninikethsai1144@gmail.com",
        "mobile_phone": "+1234567890",
        "tier_id": "membership",
        "expiry_date": "2026-12-31",
        "profile_image_url": "https://example.com/avatar.png"
    }

    processor = CreateandDistributeMemberPass()
    result = processor.process_user(sample_user)
    print("Process result:", result)