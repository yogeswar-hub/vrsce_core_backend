import requests

API_KEY = "85b59f92-615a-4f89-8dbf-39bd62f5344c"
CHAIN_ID = 658
BASE_URL = "https://clubready.com/api/current/club/{store_id}/Users/all"

def count_users(store_id: int, page_size: int = 1000) -> int:
    """
    Count unique users by Email, keeping only the record
    with the highest UserId when duplicates occur.
    """
    email_to_max_id: dict[str, int] = {}
    page = 1
    while True:
        url = BASE_URL.format(store_id=store_id)
        params = {
            "ApiKey":     API_KEY,
            "ChainId":    CHAIN_ID,
            "PageSize":   page_size,
            "PageNumber": page
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        users = resp.json()  # list of user dicts
        if not users:
            break
        for u in users:
            email = u.get("Email")
            uid = u.get("UserId") or 0
            if email:
                # keep the max UserId for each email
                prev = email_to_max_id.get(email, 0)
                if uid > prev:
                    email_to_max_id[email] = uid
        page += 1
    # the number of unique emails retained
    return len(email_to_max_id)

if __name__ == "__main__":
    store_ids = [2345, 7085, 11341, 11730, 12709, 15005]
    for sid in store_ids:
        cnt = count_users(sid)
        print(f"Store {sid}: {cnt} users")



# import requests url = "https://www.clubready.com/api/current/users"
# params = {
#     "ApiKey": "85b59f92-615a-4f89-8dbf-39bd62f5344c",
#     "ChainId": 658,
#     "ActivityDate": "01-01-2020",
#     "ActivityOperator": "GT",
#     "Segment": "All",
#     "Version": 2
# }

# response = requests.get(url, params=params)
# response.raise_for_status()

# users = response.json()  # assuming the response is a list of user objects

# print(f"✅ Total users retrieved: {len(users)}")

