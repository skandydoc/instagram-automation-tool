import os
import sys
import time
import requests

"""
carousel_post.py
Usage: python carousel_post.py <image_url_1> <image_url_2> ...

Posts the given images as an Instagram Carousel using the Facebook Graph API.
Credentials are loaded from environment variables:
    IG_USER_ID     - Instagram Business/Creator account ID
    IG_ACCESS_TOKEN- Long-lived access token with instagram_basic & instagram_content_publish scopes

The script follows these steps:
1. For each image, create a child media container (is_carousel_item=true).
2. Create a parent carousel container referencing all child container IDs.
3. Publish the carousel.

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

def create_child_container(ig_user_id: str, access_token: str, image_url: str) -> str:
    url = CREATE_ENDPOINT_TMPL.format(ig_user_id=ig_user_id)
    payload = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": access_token,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, data=payload, timeout=30)
        print(f"[DEBUG] Child container API response (status {resp.status_code}): {resp.text}")
        if resp.status_code == 200:
            creation_id = resp.json().get("id")
            if creation_id:
                print(f"[INFO] Created child container: {creation_id}")
                return creation_id
            raise RuntimeError("No creation ID returned in response.")
        print(f"[WARN] Child container creation failed (status {resp.status_code}). Attempt {attempt}/{MAX_RETRIES}. Response: {resp.text}")
        if attempt == MAX_RETRIES:
            resp.raise_for_status()
        time.sleep(RETRY_BACKOFF * attempt)

def create_carousel_container(ig_user_id: str, access_token: str, child_ids: list, caption: str = "") -> str:
    url = CREATE_ENDPOINT_TMPL.format(ig_user_id=ig_user_id)
    payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
        "access_token": access_token,
    }
    print(f"[DEBUG] Carousel payload: {payload}")
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, data=payload, timeout=30)
        print(f"[DEBUG] Carousel container API response (status {resp.status_code}): {resp.text}")
        if resp.status_code == 200:
            creation_id = resp.json().get("id")
            if creation_id:
                print(f"[INFO] Created carousel container: {creation_id}")
                return creation_id
            raise RuntimeError("No creation ID returned in response.")
        print(f"[WARN] Carousel container creation failed (status {resp.status_code}). Attempt {attempt}/{MAX_RETRIES}. Response: {resp.text}")
        if attempt == MAX_RETRIES:
            resp.raise_for_status()
        time.sleep(RETRY_BACKOFF * attempt)

def publish_carousel(ig_user_id: str, access_token: str, creation_id: str) -> str:
    url = PUBLISH_ENDPOINT_TMPL.format(ig_user_id=ig_user_id)
    payload = {
        "creation_id": creation_id,
        "access_token": access_token,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, data=payload, timeout=30)
        print(f"[DEBUG] Publish API response (status {resp.status_code}): {resp.text}")
        if resp.status_code == 200:
            publish_id = resp.json().get("id")
            if publish_id:
                print(f"[INFO] Carousel published successfully. ID: {publish_id}")
                return publish_id
            raise RuntimeError("No publish ID returned in response.")
        print(f"[WARN] Carousel publish failed (status {resp.status_code}). Attempt {attempt}/{MAX_RETRIES}. Response: {resp.text}")
        if attempt == MAX_RETRIES:
            resp.raise_for_status()
        time.sleep(RETRY_BACKOFF * attempt)

def main():
    if len(sys.argv) < 2:
        print("Usage: python carousel_post.py <image_url_1> <image_url_2> ...")
        sys.exit(1)

    image_urls = sys.argv[1:]
    ig_user_id = get_env("IG_USER_ID")
    access_token = get_env("IG_ACCESS_TOKEN")
    caption = "MBBS Quotes Carousel"

    try:
        # Step 1: Create child containers
        child_ids = []
        for url in image_urls:
            child_id = create_child_container(ig_user_id, access_token, url)
            child_ids.append(child_id)
            time.sleep(1)  # Avoid rate limits
        # Step 2: Create parent carousel container
        carousel_id = create_carousel_container(ig_user_id, access_token, child_ids, caption)
        # Step 3: Publish carousel
        publish_carousel(ig_user_id, access_token, carousel_id)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 