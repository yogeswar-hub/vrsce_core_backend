import logging
import requests
from com.dimcon.synthera_netsuite_integration.utilities.auth_service import auth_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class BaseAPI:
    """
    Base API for interacting with NetSuite provided APIs,
    performing standard CRUD operations similar to a database DAO.
    """
    def __init__(self, base_url):
        """
        Initialize the API with a base URL and obtain
        OAuth credentials from the auth service.
        """
        self.base_url = base_url.rstrip('/')
        self.auth = auth_service.get_oauth()
        logger.debug("BaseAPI initialized with base URL: %s", self.base_url)
    
    def fetch_all(self, endpoint, params=None):
        """
        Fetch a collection of records.
        
        Parameters:
            endpoint (str): The API endpoint (e.g., 'account').
            params (dict, optional): Query parameters for filtering, paging, etc.
            
        Returns:
            dict: The JSON response from the API.
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            logger.debug("GET %s with params: %s", url, params)
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            data = response.json()
            logger.debug("Fetched %s", data)
            return data
        except Exception as e:
            logger.error("Error fetching records from %s: %s", url, e, exc_info=True)
            raise

    def fetch_by_id(self, endpoint, record_id):
        """
        Fetch a single record by its identifier.
        
        Parameters:
            endpoint (str): The API endpoint.
            record_id (str): The unique identifier of the record.
            
        Returns:
            dict: The JSON response for the record.
        """
        try:
            url = f"{self.base_url}/{endpoint}/{record_id}"
            logger.debug("GET %s", url)
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            data = response.json()
            logger.debug("Fetched record: %s", data)
            return data
        except Exception as e:
            logger.error("Error fetching record %s: %s", record_id, e, exc_info=True)
            raise

    def insert(self, endpoint, data):
        """
        Insert a new record via a POST request.
        
        Parameters:
            endpoint (str): The API endpoint.
            data (dict): The data to insert.
            
        Returns:
            dict: The JSON response from the API.
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            logger.debug("POST %s with data: %s", url, data)
            response = requests.post(url, auth=self.auth, json=data)
            response.raise_for_status()
            new_record = response.json()
            logger.debug("Inserted record: %s", new_record)
            return new_record
        except Exception as e:
            logger.error("Error inserting record: %s", e, exc_info=True)
            raise

    def update(self, endpoint, record_id, data):
        """
        Update an existing record using a PUT request.
        
        Parameters:
            endpoint (str): The API endpoint.
            record_id (str): The unique identifier of the record.
            data (dict): The updated data.
            
        Returns:
            dict: The JSON response from the API.
        """
        try:
            url = f"{self.base_url}/{endpoint}/{record_id}"
            logger.debug("PUT %s with data: %s", url, data)
            response = requests.put(url, auth=self.auth, json=data)
            response.raise_for_status()
            updated_record = response.json()
            logger.debug("Updated record: %s", updated_record)
            return updated_record
        except Exception as e:
            logger.error("Error updating record %s: %s", record_id, e, exc_info=True)
            raise

    def delete(self, endpoint, record_id):
        """
        Delete a record using a DELETE request.
        
        Parameters:
            endpoint (str): The API endpoint.
            record_id (str): The unique identifier of the record.
            
        Returns:
            dict: A confirmation response from the API.
        """
        try:
            url = f"{self.base_url}/{endpoint}/{record_id}"
            logger.debug("DELETE %s", url)
            response = requests.delete(url, auth=self.auth)
            response.raise_for_status()
            logger.debug("Deleted record with id: %s", record_id)
            return {"status": "deleted", "id": record_id}
        except Exception as e:
            logger.error("Error deleting record %s: %s", record_id, e, exc_info=True)
            raise