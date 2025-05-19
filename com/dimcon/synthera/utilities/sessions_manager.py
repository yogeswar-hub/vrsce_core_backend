from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from com.dimcon.synthera.utilities.log_handler import LoggerManager
import logging  # still needed for log level constants

logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

class DBSessionUtil:
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=self.engine)
        logger.debug("DBSessionUtil initialized with provided engine.")

    @contextmanager
    def session_scope(self):
        """
        Provides a transactional scope around a series of operations.
        
        Usage:
            with DBSessionUtil(engine).session_scope() as session:
                # use session as needed
        """
        session = self.Session()
        try:
            logger.debug("Starting new session scope.")
            yield session
            session.commit()
            logger.debug("Session scope committed successfully.")
        except Exception as e:
            session.rollback()
            logger.error("Exception in session scope; rolled back session.", exc_info=True)
            raise e
        finally:
            session.close()
            logger.debug("Session scope closed.")