import os
import grpc
from passkit_io.member import a_rpc_pb2_grpc
from passkit_io.core import a_rpc_templates_pb2_grpc
from passkit_io.core import a_rpc_distribution_pb2_grpc
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__, level="DEBUG")

class GrpcClient:
    """
    Manages a gRPC channel (secure if certs exist, otherwise insecure) 
    and provides access to various PassKit service stubs.
    """

    def __init__(self, cert_dir=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cert_dir = cert_dir or os.path.normpath(os.path.join(base_dir, "..", "resources", "certs"))

        # Attempt to load TLS certs; if missing, fall back
        try:
            with open(os.path.join(cert_dir, "ca-chain.pem"), "rb") as f:
                ca_cert = f.read()
            with open(os.path.join(cert_dir, "key.pem"), "rb") as f:
                private_key = f.read()
            with open(os.path.join(cert_dir, "certificate.pem"), "rb") as f:
                cert_chain = f.read()

            logger.info(f"Certificates loaded successfully from {cert_dir}.")
            credentials = grpc.ssl_channel_credentials(
                root_certificates=ca_cert,
                private_key=private_key,
                certificate_chain=cert_chain,
            )
            self.channel = grpc.secure_channel("grpc.pub2.passkit.io:443", credentials)
            logger.info("gRPC secure channel created.")

        except FileNotFoundError:
            # Missing certs: log once and use insecure channel for dev/tests
            logger.warning(
                f"Certificate files not found in {cert_dir}; "
                "falling back to insecure channel."
            )
            self.channel = grpc.insecure_channel("grpc.pub2.passkit.io:443")

        except Exception as e:
            # Genuine loading error—re-raise
            logger.error("Unexpected error loading certificates.", exc_info=True)
            raise

    def get_members_stub(self):
        logger.debug("Creating MembersStub.")
        return a_rpc_pb2_grpc.MembersStub(self.channel)

    def get_templates_stub(self):
        logger.debug("Creating TemplatesStub.")
        return a_rpc_templates_pb2_grpc.TemplatesStub(self.channel)

    def get_distribution_stub(self):
        logger.debug("Creating DistributionStub.")
        return a_rpc_distribution_pb2_grpc.DistributionStub(self.channel)

    def get_channel(self):
        logger.debug("Returning gRPC channel.")
        return self.channel


if __name__ == "__main__":
    try:
        client = GrpcClient()
        client.get_members_stub()
        print("✅ GrpcClient initialized (with secure or insecure channel).")
    except Exception as e:
        print(f"❌ Error initializing GrpcClient: {e}")
