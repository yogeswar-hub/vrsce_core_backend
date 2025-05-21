import configparser
import boto3
import botocore.exceptions
import os  # Added here if needed

class SecretsManagerHandler:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.aws_region = None
        self.secret_cache = {}  # Cache to store retrieved secrets keyed by secret name
        self.load_config()  # Automatically load config on initialization

    def load_config(self):
        """Load configuration from the provided config file."""
        files_read = self.config.read(self.config_file)
        if not files_read:
            raise Exception(f"Configuration file '{self.config_file}' not found.")
        if not self.config.sections():
            raise Exception("No configuration sections found in the config file.")
        try:
            # Retrieve the AWS region from the 'aws' section—must be present.
            self.aws_region = self.config.get('aws', 'region').strip()
        except Exception as e:
            raise Exception("AWS region not found in configuration.") from e

    def retrieve_secret_for_section(self, section, key_name='secret_name'):
        """
        Retrieve a secret from AWS Secrets Manager for the secret defined in the given section.

        Parameters:
            section (str): The configuration section (e.g., 'database', 'netsuite').
            key_name (str): The option key holding the secret name. Defaults to 'secret_name'.

        Returns:
            str: The retrieved secret data.
        """
        if not self.aws_region:
            raise Exception("AWS region is not set. Check your configuration.")
        if not self.config.has_section(section):
            raise Exception(f"Section '{section}' not found in configuration.")
        try:
            secret_name = self.config.get(section, key_name).strip()
        except Exception as e:
            raise Exception(f"Secret name '{key_name}' not found in section '{section}'.") from e

        # If we've already retrieved this secret, return it from cache.
        if secret_name in self.secret_cache:
            return self.secret_cache[secret_name]

        try:
            secrets_manager = boto3.client('secretsmanager', region_name=self.aws_region)
            response = secrets_manager.get_secret_value(SecretId=secret_name)
            secret_data = response.get('SecretString')
            self.secret_cache[secret_name] = secret_data
            return secret_data
        except botocore.exceptions.NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure your AWS credentials.")
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceNotFoundException':
                raise Exception(f"Secret '{secret_name}' not found in AWS Secrets Manager.")
            elif error_code == 'AccessDeniedException':
                raise Exception("Access denied to AWS Secrets Manager. Check your IAM permissions.")
            else:
                raise Exception(f"AWS Secrets Manager error: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")

    @classmethod
    def get_secret(cls, config_file, section, key_name='secret_name'):
        """
        Centralized class method to load configuration and retrieve the secret for a given section.

        Parameters:
            config_file (str): The path to the configuration file.
            section (str): The section in the config file containing the secret name.
            key_name (str): The option within the section holding the secret name.

        Returns:
            str: The retrieved secret data.
        """
        handler = cls(config_file)
        return handler.retrieve_secret_for_section(section, key_name)


# Example usage (for testing purposes):
if __name__ == "__main__":
    # Compute the absolute path to config.ini located in the same folder as this module.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "config.ini")
    
    # Now call get_secret with the correct path.
    try:
        database_secret = SecretsManagerHandler.get_secret(config_file=config_path, section="database")
        print("Database Secret Data retrieved:", database_secret)
    
    except Exception as e:
        print(f"Failed to retrieve secret. Details: {e}")