import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from com.dimcon.vrse_app.utilities.log_handler import LoggerManager

logger = LoggerManager.setup_logger(__name__)

# 1) Read BASE_URL from env var, error out if unset
BASE_URL = os.getenv("CLUBREADY_BASE_URL")
if not BASE_URL:
    raise EnvironmentError("Missing required env var: CLUBREADY_BASE_URL")

class ClubReadyAPIClient:
    """
    API Client for interacting with ClubReady endpoints.
    BASE_URL is injected via environment; no hard-codes.
    """

    def __init__(self, api_key: str, chain_id: int):
        self.api_key  = api_key
        self.chain_id = chain_id
        self.params   = {"ApiKey": api_key, "ChainId": chain_id}

    def fetch_club_locations(self) -> List[dict]:
        # 2) Use the injected BASE_URL
        url = f"{BASE_URL}/corp/{self.chain_id}/clubs"
        try:
            response = requests.get(url, params=self.params, timeout=30)
            response.raise_for_status()
            logger.info("Fetched club locations from %s", url)
            return response.json()
        except requests.RequestException as e:
            logger.error("Failed to fetch club locations: %s", e)
            raise

    def fetch_all_users_parallel_dynamic(self, limit: int = 100, batch_size: int = 10) -> List[dict]:
        all_users = []
        current = 1
        while True:
            pages = range(current, current + batch_size)
            batch_results = {}

            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                # map each submitted future to its page number
                future_to_page = {
                    executor.submit(self.fetch_users, page_number, limit): page_number
                    for page_number in pages
                }
                for future in as_completed(future_to_page):
                    page_number = future_to_page[future]
                    try:
                        batch_results[page_number] = future.result()
                    except Exception as err:
                        logger.error("Error fetching page %s: %s", page_number, err)
                        batch_results[page_number] = []

            # collect and concatenate per‐page results
            for page_number in sorted(batch_results):
                users = batch_results[page_number]
                if not users:
                    return all_users
                all_users.extend(users)

            current += batch_size

    def fetch_users(self, page: int, limit: int = 100) -> List[dict]:
        url = f"{BASE_URL}/users/find"
        params = self.params.copy()
        params.update({"page": page, "limit": limit})
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json().get("users", [])
        except requests.RequestException as e:
            logger.error(f"Failed to fetch users from page {page}: {e}")
            raise

    def fetch_users_activity(self, activity_date: str, activity_operator: str, segment: str = "Active", version: int = 2) -> list:
        url = f"{BASE_URL}/users"
        params = self.params.copy()
        params.update({
            "ActivityDate": activity_date,
            "ActivityOperator": activity_operator,
            "Segment": segment,
            "Version": version
        })
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                users = payload.get("users", [])
            elif isinstance(payload, list):
                users = payload
            else:
                users = []
            logger.info(f"Fetched {len(users)} users from segment {segment}.")
            return users
        except Exception as e:
            logger.error(f"Failed to fetch active users: {e}")
            raise

    def find_user_by_email(self, email: str) -> dict:
        """
        Search for a user using email.
        """
        url = f"{BASE_URL}/users/find"
        params = self.params.copy()
        params.update({"Email": email})
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            users = response.json().get("users", [])
            if users:
                return users[0]  # return first match
            return None
        except Exception as e:
            logger.error(f"Failed to find user by email {email}: {e}")
            return None

    def find_user_by_name(self, first_name: str, last_name: str) -> dict:
        """
        Search for a user using first and last name.
        """
        url = f"{BASE_URL}/users/find"
        params = self.params.copy()
        params.update({"FirstName": first_name, "LastName": last_name})
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            users = response.json().get("users", [])
            if users:
                return users[0]  # return first match
            return None
        except Exception as e:
            logger.error(f"Failed to find user by name {first_name} {last_name}: {e}")
            return None


def fetch_users_range(api_client, start_page, end_page, limit=100, batch_size=10):
    """
    Fetch users in the given page range using api_client.fetch_users,
    in batches of up to batch_size pages at a time.
    """
    all_users = []
    pages = list(range(start_page, end_page + 1))

    for start_index in range(0, len(pages), batch_size):
        batch = pages[start_index : start_index + batch_size]
        results = {}

        with ThreadPoolExecutor(max_workers=len(batch)) as executor:
            # map each future to its page number for clarity
            future_to_page = {
                executor.submit(api_client.fetch_users, page_number, limit): page_number
                for page_number in batch
            }
            for future in as_completed(future_to_page):
                page_number = future_to_page[future]
                try:
                    results[page_number] = future.result()
                except Exception:
                    results[page_number] = []

        for page_number in sorted(results):
            all_users.extend(results[page_number])

    return all_users
