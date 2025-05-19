import configparser
import boto3
import botocore.exceptions

class SecretsManagerHandler:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.aws_region = None
        self.secret_name = None
        self.secret_data = None
        self.load_config()  # Automatically load config on initialization

    def load_config(self):
        """Load configuration from the provided config file."""
        files_read = self.config.read(self.config_file)
        if not files_read:
            raise Exception(f"Configuration file '{self.config_file}' not found.")
        if not self.config.sections():
            raise Exception("No configuration sections found in the config file.")
        try:
            # Retrieve the AWS region from the 'aws' section—must be present in the config.
            self.aws_region = self.config.get('aws', 'region').strip()
        except Exception as e:
            raise Exception("AWS region not found in configuration.") from e

        try:
            # Retrieve the secret name from the 'database' section.
            self.secret_name = self.config.get('database', 'secret_name').strip()
        except Exception as e:
            raise Exception("Database secret name not found in configuration.") from e

    def retrieve_secret(self):
        """Retrieve the secret from AWS Secrets Manager using the configuration values."""
        if not self.aws_region:
            raise Exception("AWS region is not set. Check your configuration.")
        try:
            secrets_manager = boto3.client('secretsmanager', region_name=self.aws_region)
            response = secrets_manager.get_secret_value(SecretId=self.secret_name)
            self.secret_data = response.get('SecretString')
        except botocore.exceptions.NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure your AWS credentials.")
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceNotFoundException':
                raise Exception(f"Secret '{self.secret_name}' not found in AWS Secrets Manager.")
            elif error_code == 'AccessDeniedException':
                raise Exception("Access denied to AWS Secrets Manager. Check your IAM permissions.")
            else:
                raise Exception(f"AWS Secrets Manager error: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")

    def get_secret_data(self):
        """Returns the secret data if it has been retrieved, otherwise raises an exception."""
        if self.secret_data is None:
            raise Exception("No secret data retrieved. Call 'retrieve_secret()' first.")
        return self.secret_data

    @classmethod
    def get_secrets(cls, config_file):
        """
        Centralized method to load the configuration, retrieve the secret, and return the secret data.

        Parameters:
            config_file (str): The path to the configuration file.
            
        Returns:
            str: The retrieved secret data.
        """
        handler = cls(config_file)
        handler.retrieve_secret()
        return handler.get_secret_data()

# Example usage (for testing purposes):
if __name__ == "__main__":
    try:
        # Provide the config file path dynamically (do not hardcode the file path here)
        secret_data = SecretsManagerHandler.get_secrets(config_file="path_to_your_config.ini")
        print("Secret Data retrieved:", secret_data)
    except Exception as e:
        print(f"Failed to retrieve secret. Details: {e}")