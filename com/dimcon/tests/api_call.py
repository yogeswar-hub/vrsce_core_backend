import requests

url = "https://www.clubready.com/api/current/users"
params = {
    "ApiKey": "85b59f92-615a-4f89-8dbf-39bd62f5344c",
    "ChainId": 658,
    "ActivityDate": "01-01-2020",
    "ActivityOperator": "GT",
    "Segment": "All",
    "Version": 2
}

response = requests.get(url, params=params)
response.raise_for_status()

users = response.json()  # assuming the response is a list of user objects

print(f"✅ Total users retrieved: {len(users)}")
