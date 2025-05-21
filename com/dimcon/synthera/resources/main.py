from com.dimcon.synthera.resources.base import Base  # Import the shared Base
from connect_aurora import get_engine

# Create database connection using your existing get_engine function
engine = get_engine()

# Create all tables in the database (roles first since users depends on it)
Base.metadata.create_all(engine)