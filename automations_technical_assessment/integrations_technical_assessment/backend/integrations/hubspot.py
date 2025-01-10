import json
import secrets
from fastapi import Request, HTTPException
import httpx
from integrations.integration_item import IntegrationItem
from redis_client import redis_client

# HubSpot OAuth credentials (replace with your actual credentials)
CLIENT_ID = "f7ff1e4f-46d5-4d5a-859d-c78cb8bf1f2a"
CLIENT_SECRET = "e2b7166b-0cbd-41e5-9cbf-6f412a440eae"
REDIRECT_URI = "http://localhost:8000/integrations/hubspot/oauth2callback"

async def authorize_hubspot(user_id, org_id):
    # Generate a random state token and store it in Redis
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await redis_client.set(f'hubspot_state:{org_id}:{user_id}', encoded_state, ex=600)  # Expire in 10 minutes

    # Define the scopes
    scopes = [
        "crm.objects.contacts.read",  # Read access to contacts
        "crm.objects.contacts.write",  # Write access to contacts
        "crm.schemas.contacts.read",  # Read access to contact schemas
        "crm.schemas.contacts.write",  # Write access to contact schemas
    ]
    scopes_str = "%20".join(scopes)  # Join scopes with %20 (URL-encoded space)

    authorization_url = (
        f"https://app.hubspot.com/oauth/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=oauth&"  # Required scope
        f"optional_scope={scopes_str}&"  # Optional scopes
        f"state={encoded_state}"
    )
    return {"authorization_url": authorization_url}

async def oauth2callback_hubspot(request: Request):
    code = request.query_params.get("code")
    encoded_state = request.query_params.get("state")

    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail="Authorization code or state missing")

    try:
        # Decode the state and verify it
        state_data = json.loads(encoded_state)
        user_id = state_data.get('user_id')
        org_id = state_data.get('org_id')
        original_state = state_data.get('state')

        saved_state = await redis_client.get(f'hubspot_state:{org_id}:{user_id}')
        if not saved_state or original_state != json.loads(saved_state).get('state'):
            raise HTTPException(status_code=400, detail="State does not match")

        # Exchange the authorization code for an access token
        token_url = "https://api.hubapi.com/oauth/v1/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch access token")

        credentials = response.json()
        redis_key = f"hubspot_credentials:{user_id}:{org_id}"
        await redis_client.set(redis_key, json.dumps(credentials), ex=3600)  # Expire in 1 hour

        return {"credentials": credentials}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_hubspot_credentials(user_id, org_id):
    redis_key = f"hubspot_credentials:{user_id}:{org_id}"
    credentials = await redis_client.get(redis_key)
    if not credentials:
        raise HTTPException(status_code=404, detail="Credentials not found")
    return json.loads(credentials)

async def disconnect_hubspot(user_id, org_id):
    redis_key = f"hubspot_credentials:{user_id}:{org_id}"
    await redis_client.delete(redis_key)
    return {"message": "Disconnected from HubSpot"}

async def get_items_hubspot(credentials):
    try:
        # Extract the access token from the credentials
        access_token = credentials.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Access token missing in credentials")

        # Define the HubSpot API endpoint (e.g., fetch contacts)
        url = "https://api.hubapi.com/crm/v3/objects/contacts"

        # Set up headers with the access token
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Make the API request
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from HubSpot")

        # Parse the response and extract all properties for each contact
        items = []
        for contact in response.json().get("results", []):
            # Extract all properties dynamically
            properties = contact.get("properties", {})
            item = {
                "id": contact.get("id"),  # Unique identifier for the contact
                "properties": properties  # All properties for the contact
            }
            items.append(item)

        return items

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))