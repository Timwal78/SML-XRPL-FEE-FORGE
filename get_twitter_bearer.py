import httpx
import base64
import os
from dotenv import load_dotenv

load_dotenv("C:/Users/timot/.gemini/antigravity/scratch/SML-XRPL-FEE-FORGE/SML-XRPL-FEE-FORGE/.env")

key = os.getenv("TWITTER_API_KEY")
secret = os.getenv("TWITTER_API_SECRET")

def get_bearer():
    if not key or not secret:
        print("Missing API key/secret")
        return
    
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
    }
    data = {"grant_type": "client_credentials"}
    
    resp = httpx.post("https://api.twitter.com/oauth2/token", headers=headers, data=data)
    if resp.status_code == 200:
        bearer = resp.json().get("access_token")
        print(f"BEARER_TOKEN={bearer}")
    else:
        print(f"Failed to get bearer: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    get_bearer()
