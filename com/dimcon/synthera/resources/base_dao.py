from com.dimcon.synthera.utilities.log_handler import LoggerManager
import logging
from sqlalchemy import or_

logger = LoggerManager.setup_logger(__name__, level=logging.DEBUG)

class BaseDAO:
    """
    Base Data Access Object (DAO) for interacting with the database models.
    Accepts an SQLAlchemy session and performs standard CRUD operations.
    """
    def __init__(self, engine):
        """Initialize DAO with database engine."""
        self.engine = engine
        logger.debug("BaseDAO initialized with engine.")

    def fetch_all(self, session, model, page=1, limit=10, sort_by="id", sort_order="asc", filters=None):
        """Fetch paginated and optionally sorted records for a given model."""
        if not isinstance(page, int) or page < 1:
            raise ValueError("Parameter 'page' must be a positive integer.")
        if not isinstance(limit, int) or limit < 1:
            raise ValueError("Parameter 'limit' must be a positive integer.")
        try:
            logger.debug(
                f"Fetching records from {model.__tablename__}: page={page}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}"
            )
            query = session.query(model)
            
            # Apply filters
            if filters:
                logger.debug(f"Applying filters: {filters}")
                for key, value in filters.items():
                    column = getattr(model, key, None)
                    if column is not None:
                        if isinstance(value, str):
                            # Case-insensitive match
                            query = query.filter(column.ilike(f"%{value}%"))
                        else:
                            query = query.filter(column == value)
                    else:
                        logger.warning(f"Invalid filter column: {key}")

            # Calculate total count before applying pagination.
            total_count = session.query(model).count()
            logger.debug(f"Total count for {model.__tablename__}: {total_count}")

            # Apply sorting
            if sort_by:
                sort_column = getattr(model, sort_by, None)
                if sort_column is None:
                    logger.warning(f"Sort column '{sort_by}' not found in {model.__tablename__}. Falling back to default ordering by 'id'.")
                    sort_column = getattr(model, "id", None)
                    if sort_column is None:
                        error_message = f"Default sort column 'id' not found in {model.__tablename__}."
                        logger.error(error_message)
                        raise ValueError(error_message)
                order = sort_column.desc() if sort_order.lower() == "desc" else sort_column.asc()
                query = query.order_by(order)

            # Fetch results with pagination
            results = query.limit(limit).offset((page - 1) * limit).all()
            logger.debug(f"Fetched {len(results)} records from {model.__tablename__}.")

            # Return both the results and the total count.
            return {"results": results, "total_count": total_count}
        except Exception as e:
            logger.error("Error fetching records in fetch_all.", exc_info=True)
            raise

    def fetch_by_id(self, session, model, record_id):
        """Fetch a single record by its primary key."""
        try:
            result = session.get(model, record_id)
            if not result:
                logger.debug(f"No record found with id {record_id}.")
            return result
        except Exception as e:
            logger.error(f"Error fetching record by id {record_id} in fetch_by_id.", exc_info=True)
            raise

    def insert(self, session, instance):
        """Insert a new record into the table."""
        try:
            logger.debug(f"Inserting new record into {instance.__tablename__}.")
            session.add(instance)
            session.flush()
            logger.debug("Record inserted successfully.")
            return instance
        except Exception as e:
            logger.error("Error inserting record in insert.", exc_info=True)
            raise

    def update(self, session, model, record_id, data):
        """Update an existing record by ID with new data."""
        try:
            logger.debug(f"Updating record in {model.__tablename__} with id {record_id} using data: {data}.")
            instance = session.get(model, record_id)
            if not instance:
                error_msg = f"Record with id {record_id} not found in {model.__tablename__}."
                logger.error(error_msg)
                raise ValueError(error_msg)
            for key, value in data.items():
                setattr(instance, key, value)
            logger.debug("Record updated successfully.")
            return instance
        except Exception as e:
            logger.error(f"Error updating record with id {record_id} in update.", exc_info=True)
            raise

    def delete(self, session, model, record_id):
        """Delete a record from the table by primary key."""
        try:
            logger.debug(f"Deleting record with id {record_id} from {model.__tablename__}.")
            instance = session.get(model, record_id)
            if not instance:
                error_msg = f"Record with id {record_id} not found in {model.__tablename__}."
                logger.error(error_msg)
                raise ValueError(error_msg)
            session.delete(instance)
            logger.debug("Record deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Error deleting record with id {record_id} in delete.", exc_info=True)
            raise
