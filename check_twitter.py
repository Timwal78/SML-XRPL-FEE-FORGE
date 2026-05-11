import os
import tweepy
from dotenv import load_dotenv

load_dotenv("C:/Users/timot/.gemini/antigravity/scratch/SML-XRPL-FEE-FORGE/SML-XRPL-FEE-FORGE/.env")

def check_twitter():
    key = os.getenv("TWITTER_API_KEY")
    secret = os.getenv("TWITTER_API_SECRET")
    token = os.getenv("TWITTER_ACCESS_TOKEN")
    token_secret = os.getenv("TWITTER_ACCESS_SECRET")
    
    if not all([key, secret, token, token_secret]):
        print("Missing OAuth 1.0a keys")
        return

    client = tweepy.Client(
        consumer_key=key,
        consumer_secret=secret,
        access_token=token,
        access_token_secret=token_secret
    )
    
    try:
        me = client.get_me()
        if me and me.data:
            print(f"[OK] Twitter connected as: @{me.data.username} (ID: {me.data.id})")
        else:
            print("[X] Failed to get user info")
    except Exception as e:
        print(f"[X] Twitter Error: {e}")

if __name__ == "__main__":
    check_twitter()
