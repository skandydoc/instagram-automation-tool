import os
import sys
import time
import requests
from urllib.parse import urljoin

"""story_post.py
Usage: python story_post.py <public_image_url>

Posts the given image as an Instagram Story using the Facebook Graph API.
Credentials are loaded from environment variables:
    IG_USER_ID     - Instagram Business/Creator account ID
    IG_ACCESS_TOKEN- Long-lived access token with instagram_basic & instagram_content_publish scopes

The script follows two steps:
1. Create a media container with `is_story=true`.
2. Publish the container.

It retries on transient failures and provides clear console output.
"""

CREATE_ENDPOINT_TMPL = "https://graph.facebook.com/v18.0/{ig_user_id}/media"
PUBLISH_ENDPOINT_TMPL = "https://graph.facebook.com/v18.0/{ig_user_id}/media_publish"

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds

def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"[ERROR] Environment variable '{name}' is required.")
        sys.exit(1)
    return value

def create_story_container(ig_user_id: str, access_token: str, image_url: str) -> str:
    url = CREATE_ENDPOINT_TMPL.format(ig_user_id=ig_user_id)
    payload = {
        "image_url": image_url,
        "is_story": "true",
        "access_token": access_token,
    }
    print(f"[DEBUG] Payload for story container: {payload}")
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, data=payload, timeout=30)
        print(f"[DEBUG] API response (status {resp.status_code}): {resp.text}")
        if resp.status_code == 200:
            creation_id = resp.json().get("id")
            if creation_id:
                print(f"[INFO] Created story container: {creation_id}")
                return creation_id
            raise RuntimeError("No creation ID returned in response.")
        print(f"[WARN] Story container creation failed (status {resp.status_code}). Attempt {attempt}/{MAX_RETRIES}. Response: {resp.text}")
        if attempt == MAX_RETRIES:
            resp.raise_for_status()
        time.sleep(RETRY_BACKOFF * attempt)


def publish_story(ig_user_id: str, access_token: str, creation_id: str) -> str:
    url = PUBLISH_ENDPOINT_TMPL.format(ig_user_id=ig_user_id)
    payload = {
        "creation_id": creation_id,
        "access_token": access_token,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, data=payload, timeout=30)
        if resp.status_code == 200:
            publish_id = resp.json().get("id")
            if publish_id:
                print(f"[INFO] Story published successfully. ID: {publish_id}")
                return publish_id
            raise RuntimeError("No publish ID returned in response.")
        print(f"[WARN] Story publish failed (status {resp.status_code}). Attempt {attempt}/{MAX_RETRIES}. Response: {resp.text}")
        if attempt == MAX_RETRIES:
            resp.raise_for_status()
        time.sleep(RETRY_BACKOFF * attempt)


def main():
    if len(sys.argv) != 2:
        print("Usage: python story_post.py <public_image_url>")
        sys.exit(1)

    image_url = sys.argv[1]
    ig_user_id = get_env("IG_USER_ID")
    access_token = get_env("IG_ACCESS_TOKEN")

    try:
        creation_id = create_story_container(ig_user_id, access_token, image_url)
        publish_story(ig_user_id, access_token, creation_id)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 