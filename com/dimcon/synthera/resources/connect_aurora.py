import json
from sqlalchemy import create_engine
from com.dimcon.synthera.utilities.secrets_manager import SecretsManagerHandler

def get_engine(config_file='com/dimcon/synthera/resources/config.ini'):
    # Retrieve secret data using the centralized SecretsManagerHandler
    handler = SecretsManagerHandler(config_file)
    handler.retrieve_secret()
    secret_data = handler.get_secret_data()
    
    # Parse the secret data and build the database URL dynamically
    try:
        secret_json = json.loads(secret_data)
        # Get all components required for building the database URL.
        # All these keys should be present in your secret (for instance, from AWS Secrets Manager)
        username = secret_json.get("username")
        password = secret_json.get("password")
        host     = secret_json.get("host")
        port     = secret_json.get("port")
        database = secret_json.get("dbname")
        
        # Validate that none are missing
        if not all([username, password, host, port, database]):
            missing = [k for k, v in 
                       {"username": username, "password": password, "host": host, "port": port, "database": database}.items() if not v]
            raise Exception("Missing secret data keys: " + ", ".join(missing))
        
        # Build the database URL. Adjust the dialect+driver if necessary.
        db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    except Exception as e:
        raise Exception("Failed to parse secret data: " + str(e))
    
    # Create and return the SQLAlchemy engine using the dynamically retrieved database URL
    engine = create_engine(db_url)
    return engine

# Optional: Function to check if DB connection is successful
def check_db_connection():
    """Check if the database connection is successful."""
    engine = get_engine()
    if engine:
        try:
            with engine.connect() as connection:
                print("Database connection successful!")
        except Exception as e:
            print(f"Database connection failed: {e}")

if __name__ == "__main__":
    check_db_connection()
