import os
import tweepy
from dotenv import load_dotenv

load_dotenv("C:/Users/timot/.gemini/antigravity/scratch/SML-XRPL-FEE-FORGE/SML-XRPL-FEE-FORGE/.env")

def check_v1():
    key = os.getenv("TWITTER_API_KEY")
    secret = os.getenv("TWITTER_API_SECRET")
    token = os.getenv("TWITTER_ACCESS_TOKEN")
    token_secret = os.getenv("TWITTER_ACCESS_SECRET")
    
    auth = tweepy.OAuth1UserHandler(key, secret, token, token_secret)
    api = tweepy.API(auth)
    
    try:
        user = api.verify_credentials()
        print(f"[OK] Twitter v1.1 connected: @{user.screen_name}")
    except Exception as e:
        print(f"[X] v1.1 Error: {e}")

if __name__ == "__main__":
    check_v1()
