import requests
import json

# Old tenant configuration
old_tenant = {
    "token_url": "https://zpartner.authentication.eu10.hana.ondemand.com/oauth/token",
    "csrf_url": "https://zpartner.eu10.hcs.cloud.sap/api/v1/csrf",
    "users_url": "https://zpartner.eu10.hcs.cloud.sap/api/v1/scim2/Users",
    "groups_url": "https://zpartner.eu10.hcs.cloud.sap/api/v1/scim2/Groups?count=100&filter=displayName ne \"StructuredAllocationRole_Admin\"",
    "client_id": "",  # Replace with your old tenant client ID
    "client_secret": ""  # Replace with your old tenant client secret
}

# New tenant configuration
new_tenant = {
    "token_url": "https://zpartner-sac-1.authentication.eu10.hana.ondemand.com/oauth/token",
    "csrf_url": "https://zpartner-sac-1.eu10.hcs.cloud.sap/api/v1/csrf",
    "users_url": "https://zpartner-sac-1.eu10.hcs.cloud.sap/api/v1/scim2/Users",
    "groups_post_url": "https://zpartner-sac-1.eu10.hcs.cloud.sap/api/v1/scim2/Groups",
    "client_id": "",  # Replace with your new tenant client ID
    "client_secret": ""  # Replace with your new tenant client secret
}

# Function to get OAuth token
def get_access_token(token_url, client_id, client_secret):
    payload = {"grant_type": "client_credentials"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, auth=(client_id, client_secret), headers=headers)
    response.raise_for_status()
    response_data = response.json()
    access_token = response_data.get("access_token")
    return access_token

# Function to get CSRF token
# Now also extracts and returns cookies
def get_csrf_token(csrf_url, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-csrf-token": "Fetch",
        "x-sap-sac-custom-auth": "true"
    }
    response = requests.get(csrf_url, headers=headers)
    response.raise_for_status()
    # Save the x-csrf-token from the headers
    csrf_token = response.headers.get("x-csrf-token")
    cookies = response.headers.get("Set-Cookie")  # Extract Cookie from headers
    if not csrf_token:
        raise ValueError("CSRF token not found in response headers.")
    return csrf_token, cookies

# Function to fetch users
def fetch_users(users_url, access_token, csrf_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-csrf-token": csrf_token,
        "x-sap-sac-custom-auth": "true"
    }
    response = requests.get(users_url, headers=headers)
    response.raise_for_status()
    return response.json()

# Function to fetch groups (only for old tenant)
def fetch_groups(groups_url, access_token, csrf_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-csrf-token": csrf_token,
        "x-sap-sac-custom-auth": "true"
    }
    response = requests.get(groups_url, headers=headers)
    response.raise_for_status()
    return response.json()

# Function to update group members
def update_group_members(groups_file, old_users_file, new_users_file, output_file):
    # Load the JSON files
    with open(groups_file, "r", encoding="utf-8") as f:
        groups_data = json.load(f)

    with open(old_users_file, "r", encoding="utf-8") as f:
        old_users_data = json.load(f)

    with open(new_users_file, "r", encoding="utf-8") as f:
        new_users_data = json.load(f)

    # Build mappings
    old_id_to_email = {
        user["id"]: next((email["value"] for email in user.get("emails", []) if email["primary"]), None)
        for user in old_users_data["Resources"]
    }

    email_to_new_id = {
        next((email["value"] for email in user.get("emails", []) if email["primary"]), None): user["id"]
        for user in new_users_data["Resources"]
    }

    # Update members in groups
    for group in groups_data["Resources"]:
        if "members" in group:
            for member in group["members"]:
                old_id = member.get("value")
                if old_id and old_id in old_id_to_email:
                    email = old_id_to_email[old_id]
                    if email and email in email_to_new_id:
                        new_id = email_to_new_id[email]
                        member["value"] = new_id
                        member["$ref"] = f"/api/v1/scim2/Users/{new_id}"

    # Save the updated groups data
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(groups_data, f, ensure_ascii=False, indent=4)

    print(f"Updated groups data saved to {output_file}.")

# Function to post updated groups to the new tenant
def post_groups_to_new_tenant(groups_file, groups_post_url, access_token, csrf_token, cookies):
    # Load the updated groups data
    with open(groups_file, "r", encoding="utf-8") as f:
        groups_data = json.load(f)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-csrf-token": csrf_token,
        "x-sap-sac-custom-auth": "true",
        "Cookie": cookies  # Include Cookie in headers
    }

    # Iterate over a subset of resources (test mode)
    resources = groups_data.get("Resources", [])
    for group in resources:  # Start from the second item and iterate over 4 items
        response = requests.post(groups_post_url, headers=headers, json=group)
        if response.status_code == 201:
            print(f"Group {group['displayName']} posted successfully.")
        else:
            print(f"Failed to post group {group['displayName']}: {response.status_code}, {response.text}")

# Main workflow
try:
    tokens = {}

    for tenant_name, tenant_config in {"old_tenant": old_tenant, "new_tenant": new_tenant}.items():
        print(f"Processing {tenant_name}...")
        access_token = get_access_token(tenant_config["token_url"], tenant_config["client_id"], tenant_config["client_secret"])
        csrf_token, cookies = get_csrf_token(tenant_config["csrf_url"], access_token)

        tokens[tenant_name] = {
            "access_token": access_token,
            "csrf_token": csrf_token,
            "cookies": cookies
        }

        print(f"Access Token, CSRF Token, and Cookies for {tenant_name} retrieved successfully.")

        users_data = fetch_users(tenant_config["users_url"], access_token, csrf_token)
        print(f"Users Data for {tenant_name} retrieved successfully.")

        # Save the users data to a JSON file
        output_file = f"{tenant_name}_users.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=4)
        print(f"Users data saved to {output_file}.")

        if tenant_name == "old_tenant":
            groups_data = fetch_groups(tenant_config["groups_url"], access_token, csrf_token)
            print(f"Groups Data for {tenant_name} retrieved successfully.")

            # Save the groups data to a JSON file
            groups_output_file = f"{tenant_name}_groups.json"
            with open(groups_output_file, "w", encoding="utf-8") as f:
                json.dump(groups_data, f, ensure_ascii=False, indent=4)
            print(f"Groups data saved to {groups_output_file}.")

    # Post updated groups to the new tenant
    post_groups_to_new_tenant(
        "updated_groups.json", 
        new_tenant["groups_post_url"], 
        tokens["new_tenant"]["access_token"], 
        tokens["new_tenant"]["csrf_token"], 
        tokens["new_tenant"]["cookies"]
    )

except Exception as e:
    print(f"An error occurred: {e}")
