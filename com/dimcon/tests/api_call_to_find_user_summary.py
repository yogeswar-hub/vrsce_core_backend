import requests
from collections import defaultdict

API_KEY = "85b59f92-615a-4f89-8dbf-39bd62f5344c"
CHAIN_ID = 658

BASE_URL = "https://clubready.com/api/current/users/find"

# Initialize counters
total_users = 0
store_user_count = defaultdict(int)

page = 1
while True:
    url = f"{BASE_URL}?ApiKey={API_KEY}&ChainId={CHAIN_ID}&Page={page}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f" Error on page {page}: {response.status_code}")
        break

    data = response.json()
    users = data.get("users", [])

    if not users:
        print(f" Reached end of pages at Page {page}")
        break

    for user in users:
        total_users += 1
        store_id = user.get("primary_store_id", "Unknown")
        store_user_count[store_id] += 1

    #print(f" Fetched {len(users)} users from Page {page} (Total so far: {total_users})")
    page += 1

# Final summary
print("\n ClubReady User Summary")
print(f" Total Users for Chain ID {CHAIN_ID}: {total_users}")
print("\n Users Per Store:")
for store_id, count in sorted(store_user_count.items()):
    print(f" - Store ID {store_id}: {count} users")
