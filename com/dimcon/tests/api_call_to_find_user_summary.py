# import requests
# from collections import defaultdict

# API_KEY = "85b59f92-615a-4f89-8dbf-39bd62f5344c"
# CHAIN_ID = 658

# BASE_URL = "https://clubready.com/api/current/users/find"

# # Initialize counters
# total_users = 0
# store_user_count = defaultdict(int)

# page = 1
# while True:
#     url = f"{BASE_URL}?ApiKey={API_KEY}&ChainId={CHAIN_ID}&Page={page}"
#     response = requests.get(url)

#     if response.status_code != 200:
#         print(f" Error on page {page}: {response.status_code}")
#         break

#     data = response.json()
#     users = data.get("users", [])

#     if not users:
#         print(f" Reached end of pages at Page {page}")
#         break

#     for user in users:
#         total_users += 1
#         store_id = user.get("PrimaryStoreId", "Unknown")
#         store_user_count[store_id] += 1

#     #print(f" Fetched {len(users)} users from Page {page} (Total so far: {total_users})")
#     page += 1

# # Final summary
# print("\n ClubReady User Summary")
# print(f" Total Users for Chain ID {CHAIN_ID}: {total_users}")
# print("\n Users Per Store:")
# for store_id, count in sorted(store_user_count.items()):
#     print(f" - Store ID {store_id}: {count} users")




import requests
from collections import defaultdict

API_KEY     = "85b59f92-615a-4f89-8dbf-39bd62f5344c"
CHAIN_ID    = 658
BASE_URL    = "https://clubready.com/api/current/users/find"

# 1) Fetch all pages
all_users = []
page = 1
while True:
    url = f"{BASE_URL}?ApiKey={API_KEY}&ChainId={CHAIN_ID}&Page={page}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Error on page {page}: {resp.status_code}")
        break

    batch = resp.json().get("users", [])
    if not batch:
        print(f"Reached end of pages at Page {page}")
        break

    all_users.extend(batch)
    page += 1

# 2) Deduplicate by email, keeping the record with the highest UserId
users_by_email = {}
for u in all_users:
    email = u.get("Email")
    if not email:
        continue

    # normalize
    norm = email.strip().lower()
    u["Email"] = norm

    # pick the record with the largest UserId
    existing = users_by_email.get(norm)
    if existing is None or int(u.get("UserId", 0)) > int(existing.get("UserId", 0)):
        users_by_email[norm] = u

unique_users = list(users_by_email.values())

# 3) Re-count totals & per-store
total_users = len(unique_users)
store_user_count = defaultdict(int)
for u in unique_users:
    sid = u.get("PrimaryStoreId", "Unknown")
    store_user_count[sid] += 1

# Final summary
print("\nClubReady User Summary")
print(f" Total UNIQUE Users for Chain ID {CHAIN_ID}: {total_users}")
print("\n Users Per Store:")
for store_id, count in sorted(store_user_count.items()):
    print(f" - Store ID {store_id}: {count} users")
