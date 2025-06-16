import os, json
from sqlalchemy import create_engine
from com.dimcon.vrse_app.utilities.secrets_manager import SecretsManagerHandler

def get_engine(config_file: str = 'com/dimcon/vrse_app/utilities/config.ini'):
    # pick up terraform‐injected secret name, or fall back to config.ini's secret_name
    secret_name = os.getenv("DB_SECRET_NAME")
    
    # fetch the raw secret JSON string
    if secret_name:
        secret_data = SecretsManagerHandler.get_secret(
            config_file=config_file,
            section="database",
            key_name=secret_name
        )
    else:
        secret_data = SecretsManagerHandler.get_secret(
            config_file=config_file,
            section="database"
        )

    # Parse the secret data and build the database URL dynamically
    try:
        secret_json = json.loads(secret_data)
        # Get all components required for building the database URL
        username = secret_json.get("username")
        password = secret_json.get("password")
        host     = secret_json.get("host")
        port     = secret_json.get("port")
        database = secret_json.get("db_name")
        
        # Validate that none are missing
        if not all([username, password, host, port, database]):
            missing = [
                k for k, v in {
                    "username": username,
                    "password": password,
                    "host": host,
                    "port": port,
                    "database": database
                }.items() if not v
            ]
            raise Exception("Missing secret data keys: " + ", ".join(missing))
        
        db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    except Exception:
        # you can log here if you have a logger set up
        raise

    return create_engine(db_url)

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
