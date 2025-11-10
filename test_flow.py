import requests, json, time

BASE = "http://127.0.0.1:8000"

def show(title, data):
    print(f"\n# {title}")
    try:
        print(json.dumps(data, indent=2))
    except Exception:
        print(data)

def safe_json(resp, title):
    try:
        print(f"\nResponse Status: {resp.status_code}")
        data = resp.json()
    except Exception:
        print(f"❌ Error parsing JSON for {title}")
        print(f"Response Status: {resp.status_code}")
        print(f"Response Body: {resp.text}")
        data = {}
    return data


# 1️⃣ SIGNUP (Owner & User)
print("\n🧩 Checking or creating sample users...")
requests.post(f"{BASE}/signup", json={"email": "owner5@a.com", "username": "owner5", "password": "ownerpass"})
requests.post(f"{BASE}/signup", json={"email": "user5@a.com", "username": "user5", "password": "userpass"})


# 2️⃣ Owner Login
owner_login = requests.post(f"{BASE}/login", json={"email": "owner5@a.com", "password": "ownerpass"})
owner_data = safe_json(owner_login, "Owner Login")
owner_token = owner_data.get("access_token", "")
headers_owner = {"Authorization": f"Bearer {owner_token}"}
show("Owner Login", owner_data)


# 3️⃣ User Login
user_login = requests.post(f"{BASE}/login", json={"email": "user5@a.com", "password": "userpass"})
user_data = safe_json(user_login, "User Login")
user_token = user_data.get("access_token", "")
headers_user = {"Authorization": f"Bearer {user_token}"}
show("User Login", user_data)


# 4️⃣ Register Node (by Owner)
node = requests.post(f"{BASE}/register-node", json={
    "location": "Delhi",
    "gpu_model": "RTX 4090",
    "gpu_count": 1
}, headers=headers_owner)
node_data = safe_json(node, "Register Node")
show("Node Registered", node_data)
node_id = node_data.get("id") or node_data.get("node_id") or 0
node_key = node_data.get("node_key", "")


# 5️⃣ Set Node Pricing
pricing = requests.post(f"{BASE}/pricing/{node_id}", json={
    "price_per_hour": 50.0,
    "currency": "INR"
}, headers=headers_owner)
show("Pricing Set", safe_json(pricing, "Set Pricing"))


# 6️⃣ Wallet Topup (by User)
wallet = requests.post(f"{BASE}/wallet/topup?amount=100", headers=headers_user)
show("Wallet Topup", safe_json(wallet, "Wallet Topup"))


# 7️⃣ Submit Job (by User)
job_req = requests.post(f"{BASE}/submit-job", json={
    "node_id": node_id,
    "node_key": node_key,
    "command": "echo Hello GPU!"
}, headers=headers_user)
job_data = safe_json(job_req, "Submit Job")
show("Submit Job", job_data)
job_id = job_data.get("id") or job_data.get("job_id") or 0
print(f"\n👉 Job ID set to: {job_id}")


# 8️⃣ Check Job Status
time.sleep(2)
job_status = requests.get(f"{BASE}/job-status/{job_id}", headers=headers_user)
show("Job Status", safe_json(job_status, "Job Status"))


# 9️⃣ Owner Earnings
earnings = requests.get(f"{BASE}/earnings/{node_id}", headers=headers_owner)
show("Owner Earnings", safe_json(earnings, "Owner Earnings"))
