"""
Instagram Automation Tool - Main Flask Application
Automates posting across multiple Instagram business accounts
"""

import os
import json
import random
import requests
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv
import pytz

# Google Cloud Storage imports
try:
    from google.cloud import storage
    from google.auth.exceptions import DefaultCredentialsError
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    print("Warning: Google Cloud Storage not available. Install with: pip install google-cloud-storage")

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instagram_automation.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Google Cloud Storage configuration
app.config['GCS_BUCKET_NAME'] = os.getenv('GCS_BUCKET_NAME', 'instagram-automation-storage')
app.config['GCS_PROJECT_ID'] = os.getenv('GCS_PROJECT_ID')
app.config['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Database Models
class Account(db.Model):
    """Instagram account model"""
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    instagram_id = db.Column(db.String(255), unique=True, nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    account_type = db.Column(db.String(50), default='business')
    niche = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='account', lazy=True)
    schedule = db.relationship('PostingSchedule', backref='account', lazy=True)

class Post(db.Model):
    """Post model for scheduled and published posts"""
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    post_type = db.Column(db.String(20), nullable=False, default='feed')  # 'feed', 'story', 'carousel'
    content_type = db.Column(db.String(50), nullable=False)  # 'image', 'carousel', 'story' (kept for backward compatibility)
    caption = db.Column(db.Text)
    media_urls = db.Column(db.Text)  # JSON array of image URLs
    media_files = db.Column(db.Text)  # JSON array of filenames in order (for carousels)
    hashtags = db.Column(db.Text)  # JSON array of hashtags
    story_elements = db.Column(db.Text)  # JSON object for story interactive elements
    scheduled_time = db.Column(db.DateTime, nullable=False)
    actual_post_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='scheduled')  # 'scheduled', 'posted', 'failed', 'cancelled'
    instagram_post_id = db.Column(db.String(255))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_daily_post_count(account_id, date=None):
        """Get the number of posts for a specific account on a given date"""
        if date is None:
            date = datetime.utcnow().date()
        
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        return Post.query.filter(
            Post.account_id == account_id,
            Post.scheduled_time >= start_of_day,
            Post.scheduled_time <= end_of_day,
            Post.status != 'cancelled'
        ).count()

class PostingSchedule(db.Model):
    """Posting schedule configuration for each account"""
    __tablename__ = 'posting_schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    time_slot_1 = db.Column(db.Time, nullable=False)  # Morning post time
    time_slot_2 = db.Column(db.Time, nullable=False)  # Evening post time
    timezone = db.Column(db.String(50), default='Asia/Kolkata')
    variance_minutes = db.Column(db.Integer, default=15)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class HashtagRepository(db.Model):
    """Common hashtag repository"""
    __tablename__ = 'hashtag_repository'
    
    id = db.Column(db.Integer, primary_key=True)
    hashtag = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(100))
    usage_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CaptionTemplate(db.Model):
    """Caption templates for posts"""
    __tablename__ = 'caption_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    template = db.Column(db.Text, nullable=False)
    variables = db.Column(db.Text)  # JSON array of variable names
    category = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StoryTemplate(db.Model):
    """Templates for story elements"""
    __tablename__ = 'story_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(50), nullable=False)
    template_type = db.Column(db.String(20), nullable=False)  # 'text_overlay', 'poll'
    template_data = db.Column(db.Text, nullable=False)  # JSON object with template configuration
    is_global = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MentionSuggestion(db.Model):
    """Global mention suggestions for stories"""
    __tablename__ = 'mention_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostMetrics(db.Model):
    """Enhanced analytics for all post types"""
    __tablename__ = 'post_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    metric_type = db.Column(db.String(30), nullable=False)  # 'views', 'reach', 'impressions', 'poll_responses', 'link_clicks'
    metric_value = db.Column(db.Integer, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    post = db.relationship('Post', backref='metrics', lazy=True)

# Instagram API Integration
class InstagramAPI:
    """Instagram Graph API integration class"""
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v18.0"
        self.default_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    
    def validate_access_token(self, access_token):
        """Validate if the access token is properly formatted"""
        if not access_token:
            return False, "Access token is required"
        
        if not access_token.startswith('EAA'):
            return False, "Access token format is invalid (should start with 'EAA')"
            
        if len(access_token) < 50:
            return False, "Access token appears to be too short"
            
        return True, "Valid format"
    
    def validate_account_id(self, account_id):
        """Validate if the account ID is properly formatted"""
        if not account_id:
            return False, "Instagram Account ID is required"
            
        # Instagram account IDs are typically 17-18 digit numbers
        if not account_id.isdigit():
            return False, "Instagram Account ID must be numeric"
            
        if len(account_id) < 15 or len(account_id) > 20:
            return False, "Instagram Account ID length is invalid (should be 15-20 digits)"
            
        return True, "Valid format"
    
    def get_account_info(self, account_id, access_token=None):
        """Get Instagram account information"""
        token = access_token or self.default_token
        
        # Validate inputs
        token_valid, token_msg = self.validate_access_token(token)
        if not token_valid:
            return {"error": f"Access Token Error: {token_msg}"}
            
        account_valid, account_msg = self.validate_account_id(account_id)
        if not account_valid:
            return {"error": f"Account ID Error: {account_msg}"}
        
        # Try different API endpoints for Instagram
        endpoints_to_try = [
            # Instagram Basic Display API endpoint
            f"{self.base_url}/{account_id}?fields=id,username&access_token={token}",
            # Instagram Graph API for business accounts
            f"{self.base_url}/{account_id}?fields=id,username,account_type&access_token={token}",
            # Alternative endpoint
            f"https://graph.facebook.com/v18.0/me/accounts?access_token={token}"
        ]
        
        for i, url in enumerate(endpoints_to_try):
            try:
                if i == 2:  # Special handling for me/accounts endpoint
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Look for Instagram accounts in the response
                    if 'data' in data:
                        for account in data['data']:
                            if account.get('id') == account_id:
                                return {
                                    'id': account.get('id'),
                                    'username': account.get('name', 'Unknown'),
                                    'account_type': 'business'
                                }
                    continue
                
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'error' not in data:
                        # Success - return the account info
                        return {
                            'id': data.get('id', account_id),
                            'username': data.get('username', 'Unknown'),
                            'account_type': data.get('account_type', 'business'),
                            'followers_count': data.get('followers_count', 0),
                            'media_count': data.get('media_count', 0)
                        }
                    else:
                        print(f"API Error on endpoint {i+1}: {data.get('error', {}).get('message', 'Unknown error')}")
                else:
                    print(f"HTTP {response.status_code} on endpoint {i+1}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Network error on endpoint {i+1}: {e}")
                continue
        
        # If all endpoints fail, return detailed error
        return {
            "error": "Unable to validate Instagram account. Please check:\n"
                   "1. Your Instagram Account ID is correct (17-18 digit number)\n"
                   "2. Your Access Token has proper permissions (instagram_basic, instagram_content_publish)\n"
                   "3. The account is a Business or Creator account\n"
                   "4. The account is connected to your Facebook app"
        }
    
    def upload_media(self, account_id, image_url, caption, access_token=None):
        """Upload media to Instagram (create container)"""
        token = access_token or self.default_token
        url = f"{self.base_url}/{account_id}/media"
        
        # Comprehensive logging for debugging
        print(f"\n=== INSTAGRAM API UPLOAD DEBUG ===")
        print(f"API URL: {url}")
        print(f"Account ID: {account_id}")
        print(f"Image URL: {image_url}")
        print(f"Caption length: {len(caption) if caption else 0}")
        print(f"Access token (first 20 chars): {token[:20] if token else 'None'}...")
        
        # Validate inputs
        if not image_url:
            print("ERROR: Image URL is required")
            return {"error": "Image URL is required"}
            
        if not image_url.startswith(('http://', 'https://')):
            print("ERROR: Image URL must be HTTP/HTTPS")
            return {"error": "Image URL must be a valid HTTP/HTTPS URL accessible by Instagram"}
        
        # Test image URL accessibility (key assumption to validate)
        print(f"Testing image URL accessibility...")
        
        # Special handling for localhost URLs
        if 'localhost' in image_url or '127.0.0.1' in image_url:
            print(f"DETECTED: Localhost URL - this will fail with real Instagram accounts")
            print(f"URL: {image_url}")
            
            # Test if URL is accessible locally
            try:
                image_response = requests.head(image_url, timeout=5)
                print(f"Local accessibility: {image_response.status_code}")
                
                if image_response.status_code == 200:
                    print(f"✅ Image is accessible locally")
                    print(f"❌ But Instagram CANNOT access localhost URLs")
                    return {"error": f"Instagram cannot access localhost URLs. Image is available locally but not publicly accessible. Use ngrok (ngrok http 5555) or upload to cloud storage to make it publicly accessible."}
                else:
                    print(f"❌ Image not even accessible locally: {image_response.status_code}")
                    return {"error": f"Image not accessible even locally: HTTP {image_response.status_code}"}
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Local accessibility test failed: {e}")
                return {"error": f"Cannot access image URL locally: {str(e)}"}
        
        else:
            # Test public URL accessibility
            try:
                image_response = requests.head(image_url, timeout=10)
                print(f"Public URL accessibility: {image_response.status_code}")
                print(f"Response headers: {dict(image_response.headers)}")
                
                if image_response.status_code != 200:
                    print(f"CRITICAL: Public URL not accessible (status: {image_response.status_code})")
                    return {"error": f"Image URL not accessible: HTTP {image_response.status_code}. Please check the URL and ensure it's publicly accessible."}
                else:
                    print(f"✅ Public URL is accessible - proceeding with Instagram API call")
                    
            except requests.exceptions.RequestException as e:
                print(f"CRITICAL: Cannot access public URL: {e}")
                return {"error": f"Cannot access image URL: {str(e)}. Please check the URL and network connectivity."}
        
        # Prepare request data
        data = {
            'image_url': image_url,
            'caption': caption or '',
            'access_token': token
        }
        
        print(f"Request data: {data}")
        print(f"Proceeding with Instagram API call...")
        
        try:
            print(f"Making Instagram API request...")
            response = requests.post(url, data=data, timeout=30)
            
            print(f"Instagram API response status: {response.status_code}")
            print(f"Instagram API response headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                print(f"Instagram API response body: {response_json}")
            except:
                print(f"Instagram API response text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if 'id' in result:
                    print(f"SUCCESS: Media container created with ID: {result['id']}")
                    return result
                else:
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    print(f"ERROR: API success but no ID - {error_msg}")
                    return {"error": f"Instagram API error: {error_msg}"}
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                    print(f"ERROR: API failed with message: {error_message}")
                    
                    # Analysis of common error patterns
                    if 'media type' in error_message.lower():
                        print("ANALYSIS: 'media type' error - Instagram couldn't access/validate the image")
                        print("LIKELY CAUSE: Image URL is not publicly accessible")
                        print("SOLUTION: Use ngrok, cloud storage, or public image hosting")
                    elif 'permission' in error_message.lower():
                        print("ANALYSIS: Permission error - check access token permissions")
                    elif 'account' in error_message.lower():
                        print("ANALYSIS: Account error - check account ID and type")
                    elif 'url' in error_message.lower():
                        print("ANALYSIS: URL error - image URL format or accessibility issue")
                        
                except:
                    error_message = f"HTTP {response.status_code}: {response.text}"
                    print(f"ERROR: Failed to parse error response: {error_message}")
                
                return {"error": f"Failed to upload media: {error_message}"}
                
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network error during upload: {e}")
            return {"error": f"Network error during media upload: {str(e)}"}
    
    def publish_media(self, account_id, creation_id, access_token=None):
        """Publish media container to Instagram"""
        token = access_token or self.default_token
        url = f"{self.base_url}/{account_id}/media_publish"
        
        data = {
            'creation_id': creation_id,
            'access_token': token
        }
        
        try:
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'id' in result:
                    return result
                else:
                    return {"error": f"Instagram API error: {result.get('error', {}).get('message', 'Unknown error')}"}
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                except:
                    error_message = f"HTTP {response.status_code}: {response.text}"
                
                return {"error": f"Failed to publish media: {error_message}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error during media publish: {str(e)}"}
    
    def post_to_instagram(self, account_id, image_url, caption, access_token=None):
        """Complete flow: upload and publish to Instagram"""
        
        # Check if this is a test account
        if access_token and access_token.startswith('test'):
            print(f"\n=== TEST ACCOUNT DETECTED ===")
            print(f"Account ID: {account_id}")
            print(f"Image URL: {image_url}")
            print(f"Caption: {caption[:100]}...")
            print(f"Skipping actual Instagram API call for test account")
            
            # Return success for test accounts
            return {
                "id": f"test_post_{account_id}_{int(time.time())}",
                "message": "Test post created successfully (no actual Instagram API call)"
            }
        
        # Step 1: Upload media (create container)
        upload_result = self.upload_media(account_id, image_url, caption, access_token)
        
        if not upload_result:
            return {"error": "Failed to upload media - no response from Instagram"}
        
        if 'error' in upload_result:
            return {"error": f"Upload failed: {upload_result['error']}"}
        
        if 'id' not in upload_result:
            return {"error": "Upload failed - no container ID returned"}
        
        # Step 2: Publish media
        publish_result = self.publish_media(account_id, upload_result['id'], access_token)
        
        if not publish_result:
            return {"error": "Failed to publish media - no response from Instagram"}
        
        if 'error' in publish_result:
            return {"error": f"Publish failed: {publish_result['error']}"}
        
        return publish_result
    
    def post_story(self, account_id, image_url, story_elements=None, access_token=None):
        """Post a story with interactive elements"""
        token = access_token or self.default_token
        
        # Check if this is a test account
        if token and token.startswith('test'):
            print(f"\n=== TEST STORY POST ===")
            print(f"Account ID: {account_id}")
            print(f"Image URL: {image_url}")
            print(f"Story Elements: {story_elements}")
            return {
                "id": f"test_story_{account_id}_{int(time.time())}",
                "message": "Test story created successfully"
            }
        
        # For real accounts, implement story posting
        url = f"{self.base_url}/{account_id}/media"
        
        # Base story data
        data = {
            'image_url': image_url,
            'media_type': 'STORIES',
            'access_token': token
        }
        
        # Add story elements if provided
        if story_elements:
            # Add text overlay
            if 'text_overlay' in story_elements:
                text_data = story_elements['text_overlay']
                data['text'] = text_data.get('text', '')
                data['text_color'] = text_data.get('color', '#FFFFFF')
                data['text_position'] = text_data.get('position', 'center')
            
            # Add poll
            if 'poll' in story_elements:
                poll_data = story_elements['poll']
                data['poll_question'] = poll_data.get('question', '')
                data['poll_options'] = json.dumps(poll_data.get('options', []))
            
            # Add mentions
            if 'mentions' in story_elements:
                data['user_tags'] = json.dumps([{'username': mention.replace('@', '')} 
                                               for mention in story_elements['mentions']])
            
            # Add link
            if 'link' in story_elements:
                link_data = story_elements['link']
                data['action_url'] = link_data.get('url', '')
                data['cta_type'] = 'LEARN_MORE'
        
        try:
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'id' in result:
                    return self.publish_media(account_id, result['id'], token)
                else:
                    return {"error": f"Story creation failed: {result.get('error', {}).get('message', 'Unknown error')}"}
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                return {"error": f"Failed to create story: {error_message}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error during story creation: {str(e)}"}
    
    def post_carousel(self, account_id, image_urls, caption, access_token=None):
        """Post a carousel with multiple images"""
        token = access_token or self.default_token
        
        # Check if this is a test account
        if token and token.startswith('test'):
            print(f"\n=== TEST CAROUSEL POST ===")
            print(f"Account ID: {account_id}")
            print(f"Image URLs: {image_urls}")
            print(f"Caption: {caption[:100]}...")
            return {
                "id": f"test_carousel_{account_id}_{int(time.time())}",
                "message": "Test carousel created successfully"
            }
        
        # For real accounts, implement carousel posting
        # Step 1: Create individual media containers for each image
        media_ids = []
        
        for i, image_url in enumerate(image_urls):
            container_url = f"{self.base_url}/{account_id}/media"
            container_data = {
                'image_url': image_url,
                'is_carousel_item': 'true',
                'access_token': token
            }
            
            try:
                response = requests.post(container_url, data=container_data)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'id' in result:
                        media_ids.append(result['id'])
                        print(f"Created container {i+1}/{len(image_urls)}: {result['id']}")
                    else:
                        return {"error": f"Failed to create container for image {i+1}: {result.get('error', {}).get('message', 'Unknown error')}"}
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                    return {"error": f"Failed to create container for image {i+1}: {error_message}"}
                    
            except requests.exceptions.RequestException as e:
                return {"error": f"Network error creating container for image {i+1}: {str(e)}"}
        
        # Step 2: Create carousel container
        carousel_url = f"{self.base_url}/{account_id}/media"
        carousel_data = {
            'media_type': 'CAROUSEL',
            'children': ','.join(media_ids),
            'caption': caption,
            'access_token': token
        }
        
        try:
            response = requests.post(carousel_url, data=carousel_data)
            
            if response.status_code == 200:
                result = response.json()
                if 'id' in result:
                    # Step 3: Publish the carousel
                    return self.publish_media(account_id, result['id'], token)
                else:
                    return {"error": f"Carousel creation failed: {result.get('error', {}).get('message', 'Unknown error')}"}
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                return {"error": f"Failed to create carousel: {error_message}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error during carousel creation: {str(e)}"}
    
    def collect_post_metrics(self, post_id, post_type, access_token=None):
        """Collect metrics for a published post"""
        token = access_token or self.default_token
        
        # Check if this is a test account
        if token and token.startswith('test'):
            # Return mock metrics for test accounts
            return {
                'views': random.randint(100, 1000),
                'reach': random.randint(80, 800),
                'impressions': random.randint(120, 1200),
                'engagement': random.randint(10, 100)
            }
        
        # For real accounts, fetch metrics from Instagram API
        url = f"{self.base_url}/{post_id}/insights"
        
        # Determine metrics based on post type
        if post_type == 'story':
            metrics = 'impressions,reach,profile_views,story_exits'
        elif post_type == 'carousel':
            metrics = 'impressions,reach,saved,video_views'
        else:  # feed post
            metrics = 'impressions,reach,saved,likes,comments'
        
        params = {
            'metric': metrics,
            'access_token': token
        }
        
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                metrics_dict = {}
                
                for metric_data in data.get('data', []):
                    metric_name = metric_data.get('name')
                    metric_values = metric_data.get('values', [])
                    if metric_values:
                        metrics_dict[metric_name] = metric_values[0].get('value', 0)
                
                return metrics_dict
            else:
                print(f"Failed to fetch metrics for {post_id}: HTTP {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching metrics for {post_id}: {e}")
            return {}

# Global Instagram API instance
instagram_api = InstagramAPI()

# Utility Functions
def detect_ngrok_url():
    """Detect if ngrok is running and get the public URL"""
    try:
        # Check environment variable first
        ngrok_url = os.getenv('NGROK_URL')
        if ngrok_url:
            # Validate the URL
            response = requests.head(ngrok_url, timeout=5)
            if response.status_code < 400:
                return ngrok_url.rstrip('/')
    except:
        pass
    
    try:
        # Try to get ngrok tunnels from ngrok API
        response = requests.get('http://127.0.0.1:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            data = response.json()
            for tunnel in data.get('tunnels', []):
                if tunnel.get('config', {}).get('addr') == 'http://localhost:5555':
                    public_url = tunnel.get('public_url')
                    if public_url and public_url.startswith('https://'):
                        return public_url.rstrip('/')
    except:
        pass
    
    return None

def validate_image_accessibility(image_url):
    """Validate that an image URL is accessible"""
    try:
        response = requests.head(image_url, timeout=10)
        return response.status_code == 200, response.status_code
    except requests.exceptions.RequestException as e:
        return False, str(e)

def calculate_post_time(base_time, variance_minutes=15):
    """Calculate actual posting time with random variance"""
    variance_seconds = variance_minutes * 60
    random_offset = random.randint(-variance_seconds, variance_seconds)
    return base_time + timedelta(seconds=random_offset)

# File Upload Helper Functions
def create_account_folder_structure(account_id):
    """Create folder structure for account-specific uploads"""
    base_path = app.config['UPLOAD_FOLDER']
    folders = ['feed', 'stories', 'carousels']
    
    for folder in folders:
        folder_path = os.path.join(base_path, str(account_id), folder)
        os.makedirs(folder_path, exist_ok=True)
    
    return True

def parse_filename_order(files):
    """Parse filenames and extract numeric ordering"""
    file_order = []
    
    for file in files:
        filename = file.filename
        # Extract numbers from filename
        import re
        numbers = re.findall(r'\d+', filename)
        
        if numbers:
            # Use the first number found as order
            order = int(numbers[0])
        else:
            # Fallback to alphabetical order
            order = ord(filename[0].lower()) if filename else 999
        
        file_order.append((order, file))
    
    # Sort by order
    file_order.sort(key=lambda x: x[0])
    
    return [file for order, file in file_order]

def save_files_to_account_folder(files, account_id, post_type):
    """Save multiple files to account-specific folder structure"""
    saved_files = []
    
    # Ensure folder structure exists
    create_account_folder_structure(account_id)
    
    # Determine folder based on post type
    folder_name = 'feed'  # default
    if post_type == 'story':
        folder_name = 'stories'
    elif post_type == 'carousel':
        folder_name = 'carousels'
    
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], str(account_id), folder_name)
    
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            unique_filename = f"{timestamp}_{name}{ext}"
            
            file_path = os.path.join(base_path, unique_filename)
            file.save(file_path)
            
            saved_files.append({
                'original_name': filename,
                'saved_name': unique_filename,
                'file_path': file_path,
                'relative_path': f"{account_id}/{folder_name}/{unique_filename}"
            })
    
    return saved_files

# Google Cloud Storage Functions
class GoogleCloudStorage:
    """Google Cloud Storage helper class"""
    
    def __init__(self):
        self.bucket_name = app.config['GCS_BUCKET_NAME']
        self.project_id = app.config['GCS_PROJECT_ID']
        self.client = None
        self.bucket = None
        self.available = GCS_AVAILABLE
        self.authenticated = False
        
        if self.available:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize GCS client with authentication"""
        try:
            # Try to initialize the client
            if self.project_id:
                self.client = storage.Client(project=self.project_id)
            else:
                self.client = storage.Client()
            
            # Test authentication by trying to get bucket info
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Test if bucket exists and is accessible
            if self.bucket.exists():
                self.authenticated = True
                print(f"✅ Google Cloud Storage initialized successfully")
                print(f"   Bucket: {self.bucket_name}")
                print(f"   Project: {self.project_id or 'default'}")
            else:
                print(f"⚠️  GCS Bucket '{self.bucket_name}' does not exist or is not accessible")
                self.authenticated = False
                
        except DefaultCredentialsError:
            print(f"❌ GCS Authentication failed: No valid credentials found")
            print(f"   Set GOOGLE_APPLICATION_CREDENTIALS or use: gcloud auth application-default login")
            self.authenticated = False
        except Exception as e:
            print(f"❌ GCS Initialization failed: {e}")
            self.authenticated = False
    
    def is_available(self):
        """Check if GCS is available and authenticated"""
        return self.available and self.authenticated
    
    def upload_file(self, file_obj, filename, content_type=None):
        """Upload file to Google Cloud Storage"""
        if not self.is_available():
            return None, "Google Cloud Storage not available or not authenticated"
        
        try:
            # Generate unique filename with timestamp
            timestamp = int(time.time())
            safe_filename = secure_filename(filename)
            unique_filename = f"instagram_uploads/{timestamp}_{safe_filename}"
            
            # Create blob and upload
            blob = self.bucket.blob(unique_filename)
            
            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            
            # Upload file
            file_obj.seek(0)  # Reset file pointer
            blob.upload_from_file(file_obj)
            
            # Make blob publicly readable
            blob.make_public()
            
            # Get public URL
            public_url = blob.public_url
            
            print(f"✅ File uploaded to GCS successfully")
            print(f"   Filename: {unique_filename}")
            print(f"   Public URL: {public_url}")
            
            return public_url, None
            
        except Exception as e:
            error_msg = f"Failed to upload to Google Cloud Storage: {str(e)}"
            print(f"❌ {error_msg}")
            return None, error_msg
    
    def get_status(self):
        """Get detailed status of GCS configuration"""
        status = {
            'available': self.available,
            'authenticated': self.authenticated,
            'bucket_name': self.bucket_name,
            'project_id': self.project_id,
            'bucket_exists': False
        }
        
        if self.authenticated and self.bucket:
            try:
                status['bucket_exists'] = self.bucket.exists()
            except:
                status['bucket_exists'] = False
        
        return status

# Initialize GCS instance
gcs = GoogleCloudStorage()

def get_random_hashtags(count=20):
    """Get random hashtags from repository"""
    hashtags = HashtagRepository.query.filter_by(is_active=True).all()
    if len(hashtags) <= count:
        return [h.hashtag for h in hashtags]
    return [h.hashtag for h in random.sample(hashtags, count)]

def process_caption_template(template, custom_text="", account_name=""):
    """Process caption template with variables"""
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    # Determine time period
    hour = now.hour
    if 5 <= hour < 12:
        time_period = "morning"
    elif 12 <= hour < 17:
        time_period = "afternoon"
    elif 17 <= hour < 21:
        time_period = "evening"
    else:
        time_period = "night"
    
    # Replace variables
    processed = template.replace('{account_name}', account_name)
    processed = processed.replace('{date}', now.strftime('%B %d, %Y'))
    processed = processed.replace('{time}', now.strftime('%I:%M %p'))
    processed = processed.replace('{day_of_week}', now.strftime('%A'))
    processed = processed.replace('{time_period}', time_period)
    processed = processed.replace('{custom_text}', custom_text)
    
    return processed

# Background job for posting
def execute_scheduled_post(post_id):
    """Execute a scheduled post"""
    with app.app_context():
        post = Post.query.get(post_id)
        if not post or post.status != 'scheduled':
            return
        
        try:
            # Get account info
            account = Account.query.get(post.account_id)
            if not account or not account.is_active:
                post.status = 'failed'
                post.error_message = 'Account not found or inactive'
                db.session.commit()
                return
            
            # Get media URLs
            media_urls = json.loads(post.media_urls) if post.media_urls else []
            if not media_urls:
                post.status = 'failed'
                post.error_message = 'No media URLs found'
                db.session.commit()
                return
            
            # Handle different post types
            if post.post_type == 'story':
                # Post story
                image_url = media_urls[0]
                story_elements = json.loads(post.story_elements) if post.story_elements else {}
                
                result = instagram_api.post_story(
                    account.instagram_id,
                    image_url,
                    story_elements,
                    account.access_token
                )
            elif post.post_type == 'carousel':
                # Post carousel
                result = instagram_api.post_carousel(
                    account.instagram_id,
                    media_urls,
                    post.caption,
                    account.access_token
                )
            else:
                # Default to feed post
                image_url = media_urls[0]
                
                result = instagram_api.post_to_instagram(
                    account.instagram_id,
                    image_url,
                    post.caption,
                    account.access_token
                )
            
            if result and 'id' in result:
                post.status = 'posted'
                post.instagram_post_id = result['id']
                post.actual_post_time = datetime.utcnow()
                print(f"Successfully posted to Instagram: {result['id']}")
            elif result and 'error' in result:
                post.status = 'failed'
                post.error_message = result['error']
                print(f"Failed to post: {result['error']}")
            else:
                post.status = 'failed'
                post.error_message = 'Unknown error occurred while posting to Instagram'
                print(f"Failed to post: {result}")
            
        except Exception as e:
            post.status = 'failed'
            post.error_message = str(e)
            print(f"Error executing scheduled post: {e}")
        
        post.updated_at = datetime.utcnow()
        db.session.commit()

# Routes
@app.route('/')
def index():
    """Main dashboard"""
    accounts = Account.query.filter_by(is_active=True).all()
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
    
    # Quick stats
    total_posts = Post.query.count()
    successful_posts = Post.query.filter_by(status='posted').count()
    failed_posts = Post.query.filter_by(status='failed').count()
    pending_posts = Post.query.filter_by(status='scheduled').count()
    
    stats = {
        'total_posts': total_posts,
        'successful_posts': successful_posts,
        'failed_posts': failed_posts,
        'pending_posts': pending_posts,
        'success_rate': round((successful_posts / total_posts * 100) if total_posts > 0 else 0, 1)
    }
    
    return render_template('dashboard.html', 
                         accounts=accounts, 
                         recent_posts=recent_posts,
                         stats=stats)

@app.route('/accounts')
def accounts():
    """Account management page"""
    accounts = Account.query.all()
    return render_template('accounts.html', accounts=accounts)

@app.route('/add_account', methods=['GET', 'POST'])
def add_account():
    """Add new Instagram account"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        instagram_id = request.form['instagram_id'].strip()
        access_token = request.form['access_token'].strip()
        niche = request.form.get('niche', '').strip()
        
        # Basic validation
        if not username or not instagram_id or not access_token:
            flash('All required fields must be filled out', 'error')
            return render_template('add_account.html')
        
        # Check if account already exists
        existing_account = Account.query.filter(
            (Account.username == username) | (Account.instagram_id == instagram_id)
        ).first()
        
        if existing_account:
            flash('An account with this username or Instagram ID already exists', 'error')
            return render_template('add_account.html')
        
        # Check if this is a test account (for development/testing)
        is_test_account = (username.startswith('test_') or 
                          instagram_id.startswith('test') or 
                          access_token.startswith('test'))
        
        if is_test_account:
            # Skip API validation for test accounts
            account = Account(
                username=username,
                instagram_id=instagram_id,
                access_token=access_token,
                niche=niche,
                account_type='business'
            )
            
            db.session.add(account)
            db.session.commit()
            
            # Create default posting schedule
            schedule = PostingSchedule(
                account_id=account.id,
                time_slot_1=datetime.strptime('13:00', '%H:%M').time(),  # 1 PM
                time_slot_2=datetime.strptime('22:00', '%H:%M').time()   # 10 PM
            )
            db.session.add(schedule)
            db.session.commit()
            
            flash(f'Test account @{username} added successfully! (Test mode - no API validation)', 'success')
            return redirect(url_for('accounts'))
        
        # Validate account with Instagram API for real accounts
        try:
            account_info = instagram_api.get_account_info(instagram_id, access_token)
            
            if not account_info:
                flash('Unable to connect to Instagram API. Please try again later.', 'error')
                return render_template('add_account.html')
            
            if 'error' in account_info:
                flash(f'Instagram API Error: {account_info["error"]}', 'error')
                return render_template('add_account.html')
            
            # Verify the account ID matches what Instagram returns
            if account_info.get('id') != instagram_id:
                flash(f'Account ID mismatch. Instagram returned ID: {account_info.get("id", "unknown")}', 'error')
                return render_template('add_account.html')
            
            # Use the username from Instagram if available, otherwise use provided username
            instagram_username = account_info.get('username', username)
            
            # Create account
            account = Account(
                username=instagram_username,
                instagram_id=instagram_id,
                access_token=access_token,
                niche=niche,
                account_type=account_info.get('account_type', 'business')
            )
            
            db.session.add(account)
            db.session.commit()
            
            # Create default posting schedule
            schedule = PostingSchedule(
                account_id=account.id,
                time_slot_1=datetime.strptime('13:00', '%H:%M').time(),  # 1 PM
                time_slot_2=datetime.strptime('22:00', '%H:%M').time()   # 10 PM
            )
            db.session.add(schedule)
            db.session.commit()
            
            flash(f'Account @{instagram_username} added successfully! Account type: {account_info.get("account_type", "business")}', 'success')
            return redirect(url_for('accounts'))
            
        except Exception as e:
            flash(f'Error validating account: {str(e)}', 'error')
            return render_template('add_account.html')
    
    return render_template('add_account.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload and schedule posts - supports Feed, Stories, and Carousels"""
    if request.method == 'POST':
        try:
            # Debug logging
            print(f"Upload POST request received")
            print(f"Content-Type: {request.content_type}")
            print(f"Content-Length: {request.content_length}")
            print(f"Form data: {dict(request.form)}")
            print(f"Files in request: {list(request.files.keys())}")
            
            # Get post type and basic form data
            post_type = request.form.get('post_type', 'feed')
            account_id = request.form.get('account_id')
            schedule_type = request.form.get('schedule_type', 'now')
            
            print(f"Post type: {post_type}")
            print(f"Account ID: {account_id}")
            print(f"Schedule type: {schedule_type}")
            
            # Validate account selection
            if not account_id:
                flash('Please select an Instagram account', 'error')
                accounts = Account.query.filter_by(is_active=True).all()
                templates = CaptionTemplate.query.filter_by(is_active=True).all()
                return render_template('upload.html', accounts=accounts, templates=templates)
            
            account = Account.query.get(account_id)
            if not account:
                flash('Account not found', 'error')
                accounts = Account.query.filter_by(is_active=True).all()
                templates = CaptionTemplate.query.filter_by(is_active=True).all()
                return render_template('upload.html', accounts=accounts, templates=templates)
            
            # Check daily post limit (max 25 posts per day per account)
            daily_count = Post.get_daily_post_count(account_id)
            if daily_count >= 25:
                flash('Daily post limit reached (25 posts). Posts will be queued for tomorrow.', 'warning')
                # Automatically adjust schedule to next day
                tomorrow = datetime.utcnow().date() + timedelta(days=1)
                scheduled_time = datetime.combine(tomorrow, datetime.min.time().replace(hour=6))  # 6 AM next day
            else:
                scheduled_time = None  # Will be calculated based on schedule_type
            
            # Handle different post types
            if post_type == 'feed':
                result = handle_feed_post(request, account, schedule_type, scheduled_time)
            elif post_type == 'story':
                result = handle_story_post(request, account, schedule_type, scheduled_time)
            elif post_type == 'carousel':
                result = handle_carousel_post(request, account, schedule_type, scheduled_time)
            else:
                flash('Invalid post type', 'error')
                return redirect(url_for('upload'))
            
            if result.get('success'):
                flash(result.get('message', 'Post scheduled successfully!'), 'success')
                return redirect(url_for('posts'))
            else:
                flash(result.get('error', 'Unknown error occurred'), 'error')
                accounts = Account.query.filter_by(is_active=True).all()
                templates = CaptionTemplate.query.filter_by(is_active=True).all()
                return render_template('upload.html', accounts=accounts, templates=templates)
            
        except Exception as e:
            print(f"Error in upload route: {e}")
            flash(f'Error uploading post: {str(e)}', 'error')
            return redirect(url_for('upload'))
    
    # GET request - show upload form
    accounts = Account.query.filter_by(is_active=True).all()
    templates = CaptionTemplate.query.filter_by(is_active=True).all()
    
    return render_template('upload.html', accounts=accounts, templates=templates)

# Post type handlers
def handle_feed_post(request, account, schedule_type, override_scheduled_time=None):
    """Handle feed post upload and scheduling"""
    try:
        # Get form data
        caption_template = request.form.get('caption_template', '')
        custom_text = request.form.get('custom_text', '')
        
        # Validate caption content
        if not custom_text.strip() and not caption_template:
            return {'error': 'Please enter caption text or select a template'}
        
        # Handle file upload
        if 'file' not in request.files:
            return {'error': 'No file was uploaded. Please select an image file.'}
        
        file = request.files['file']
        if not file or file.filename == '':
            return {'error': 'No file was selected. Please choose an image file.'}
        
        # Save file to account-specific folder
        saved_files = save_files_to_account_folder([file], account.id, 'feed')
        if not saved_files:
            return {'error': 'Failed to save uploaded file'}
        
        saved_file = saved_files[0]
        
        # Get public URL for the image
        image_url = get_public_url_for_file(saved_file, account)
        if not image_url:
            return {'error': 'Failed to get public URL for image'}
        
        # Process caption
        if caption_template:
            caption = process_caption_template(caption_template, custom_text, account.username)
        else:
            caption = custom_text
        
        # Add hashtags
        hashtags = get_random_hashtags(20)
        if hashtags:
            caption += '\n\n' + ' '.join(f'#{tag}' for tag in hashtags)
        
        # Calculate scheduled time
        if override_scheduled_time:
            scheduled_time = override_scheduled_time
        else:
            scheduled_time = calculate_scheduled_time(schedule_type, account.id)
        
        # Create post record
        post = Post(
            account_id=account.id,
            post_type='feed',
            content_type='image',
            caption=caption,
            media_urls=json.dumps([image_url]),
            media_files=json.dumps([saved_file['saved_name']]),
            scheduled_time=scheduled_time
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Schedule the post
        schedule_post_execution(post, schedule_type)
        
        return {'success': True, 'message': 'Feed post scheduled successfully!'}
        
    except Exception as e:
        print(f"Error in handle_feed_post: {e}")
        return {'error': f'Error creating feed post: {str(e)}'}

def handle_story_post(request, account, schedule_type, override_scheduled_time=None):
    """Handle story post upload and scheduling"""
    try:
        # Handle file upload
        if 'file' not in request.files:
            return {'error': 'No image was uploaded for the story'}
        
        file = request.files['file']
        if not file or file.filename == '':
            return {'error': 'No story image was selected'}
        
        # Save file to account-specific folder
        saved_files = save_files_to_account_folder([file], account.id, 'story')
        if not saved_files:
            return {'error': 'Failed to save story image'}
        
        saved_file = saved_files[0]
        
        # Get public URL for the image
        image_url = get_public_url_for_file(saved_file, account)
        if not image_url:
            return {'error': 'Failed to get public URL for story image'}
        
        # Parse story elements from form
        story_elements = {}
        
        # Text overlay
        overlay_text = request.form.get('overlay_text', '').strip()
        if overlay_text:
            story_elements['text_overlay'] = {
                'text': overlay_text,
                'position': request.form.get('text_position', 'center'),
                'style': request.form.get('text_style', 'default')
            }
        
        # Poll
        poll_question = request.form.get('poll_question', '').strip()
        if poll_question:
            poll_options = []
            for i in range(1, 5):  # 4 poll options
                option = request.form.get(f'poll_option_{i}', '').strip()
                if option:
                    poll_options.append(option)
            
            if len(poll_options) >= 2:
                story_elements['poll'] = {
                    'question': poll_question,
                    'options': poll_options
                }
        
        # Parse story elements JSON (from JavaScript)
        story_elements_json = request.form.get('story_elements', '')
        if story_elements_json:
            try:
                js_elements = json.loads(story_elements_json)
                story_elements.update(js_elements)
            except json.JSONDecodeError:
                pass
        
        # Calculate scheduled time
        if override_scheduled_time:
            scheduled_time = override_scheduled_time
        else:
            scheduled_time = calculate_story_schedule_time(schedule_type, account.id)
        
        # Create post record
        post = Post(
            account_id=account.id,
            post_type='story',
            content_type='story',
            caption='',  # Stories don't have captions
            media_urls=json.dumps([image_url]),
            media_files=json.dumps([saved_file['saved_name']]),
            story_elements=json.dumps(story_elements) if story_elements else None,
            scheduled_time=scheduled_time
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Schedule the post
        schedule_post_execution(post, schedule_type)
        
        return {'success': True, 'message': 'Story scheduled successfully!'}
        
    except Exception as e:
        print(f"Error in handle_story_post: {e}")
        return {'error': f'Error creating story: {str(e)}'}

def handle_carousel_post(request, account, schedule_type, override_scheduled_time=None):
    """Handle carousel post upload and scheduling"""
    try:
        # Get caption
        caption = request.form.get('caption', '').strip()
        caption_template = request.form.get('caption_template', '')
        
        if not caption and not caption_template:
            return {'error': 'Please enter a caption for your carousel'}
        
        # Handle multiple file uploads
        if 'files[]' not in request.files:
            return {'error': 'No images were uploaded for the carousel'}
        
        files = request.files.getlist('files[]')
        if not files or len(files) == 0:
            return {'error': 'No carousel images were selected'}
        
        if len(files) > 20:
            return {'error': 'Maximum 20 images allowed for carousel'}
        
        # Parse file order from JavaScript
        file_order_json = request.form.get('file_order', '')
        if file_order_json:
            try:
                file_order = json.loads(file_order_json)
                # Reorder files based on the order from frontend
                files = sort_files_by_order(files, file_order)
            except json.JSONDecodeError:
                # Fallback to filename-based ordering
                files = parse_filename_order(files)
        else:
            # Fallback to filename-based ordering
            files = parse_filename_order(files)
        
        # Save files to account-specific folder
        saved_files = save_files_to_account_folder(files, account.id, 'carousel')
        if not saved_files:
            return {'error': 'Failed to save carousel images'}
        
        # Get public URLs for all images
        image_urls = []
        for saved_file in saved_files:
            image_url = get_public_url_for_file(saved_file, account)
            if not image_url:
                return {'error': f'Failed to get public URL for {saved_file["original_name"]}'}
            image_urls.append(image_url)
        
        # Process caption
        if caption_template:
            final_caption = process_caption_template(caption_template, caption, account.username)
        else:
            final_caption = caption
        
        # Add hashtags
        hashtags = get_random_hashtags(20)
        if hashtags:
            final_caption += '\n\n' + ' '.join(f'#{tag}' for tag in hashtags)
        
        # Calculate scheduled time
        if override_scheduled_time:
            scheduled_time = override_scheduled_time
        else:
            scheduled_time = calculate_scheduled_time(schedule_type, account.id)
        
        # Create post record
        post = Post(
            account_id=account.id,
            post_type='carousel',
            content_type='carousel',
            caption=final_caption,
            media_urls=json.dumps(image_urls),
            media_files=json.dumps([f['saved_name'] for f in saved_files]),
            scheduled_time=scheduled_time
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Schedule the post
        schedule_post_execution(post, schedule_type)
        
        return {'success': True, 'message': f'Carousel with {len(image_urls)} images scheduled successfully!'}
        
    except Exception as e:
        print(f"Error in handle_carousel_post: {e}")
        return {'error': f'Error creating carousel: {str(e)}'}

def sort_files_by_order(files, file_order):
    """Sort files based on the order array from frontend"""
    file_dict = {f.filename: f for f in files}
    sorted_files = []
    
    for filename in file_order:
        if filename in file_dict:
            sorted_files.append(file_dict[filename])
    
    # Add any remaining files not in the order
    for file in files:
        if file not in sorted_files:
            sorted_files.append(file)
    
    return sorted_files

def get_public_url_for_file(saved_file, account):
    """Get public URL for a saved file"""
    is_test_account = account.access_token.startswith('test')
    
    if is_test_account:
        # For test accounts, use localhost URL
        return f"http://localhost:5555/uploads/{saved_file['relative_path']}"
    else:
        # For real accounts, try Google Cloud Storage first, then ngrok
        if gcs.is_available():
            try:
                with open(saved_file['file_path'], 'rb') as gcs_file:
                    public_url, gcs_error = gcs.upload_file(
                        gcs_file, 
                        saved_file['saved_name'], 
                        'image/jpeg'  # Default content type
                    )
                    
                if public_url:
                    return public_url
                else:
                    print(f"❌ GCS upload failed: {gcs_error}")
            except Exception as e:
                print(f"❌ GCS upload error: {e}")
        
        # Fallback to ngrok
        ngrok_url = detect_ngrok_url()
        if ngrok_url:
            return f"{ngrok_url}/uploads/{saved_file['relative_path']}"
        
        # No public URL available
        return None

def calculate_scheduled_time(schedule_type, account_id):
    """Calculate scheduled time based on schedule type"""
    if schedule_type == 'now':
        return datetime.utcnow()
    elif schedule_type == 'next_slot':
        return get_next_available_slot(account_id)
    elif schedule_type == 'specific':
        # This would need to be handled in the calling function with specific time
        return datetime.utcnow()
    else:
        return datetime.utcnow()

def calculate_story_schedule_time(schedule_type, account_id):
    """Calculate scheduled time for stories with auto-scheduling"""
    if schedule_type == 'now':
        return datetime.utcnow()
    elif schedule_type == 'auto_story':
        # Auto-schedule stories every 2 hours from 6 AM to 2 AM (10 stories per day)
        return get_next_story_slot(account_id)
    elif schedule_type == 'queue':
        return queue_next_available_time(account_id, 'story')
    else:
        return datetime.utcnow()

def get_next_available_slot(account_id):
    """Get next available posting slot for the account"""
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    schedule = PostingSchedule.query.filter_by(account_id=account_id, is_active=True).first()
    
    if schedule:
        # Check if we can post today
        slot1_today = datetime.combine(now.date(), schedule.time_slot_1)
        slot2_today = datetime.combine(now.date(), schedule.time_slot_2)
        
        if now.time() < schedule.time_slot_1:
            scheduled_time = calculate_post_time(slot1_today, schedule.variance_minutes)
        elif now.time() < schedule.time_slot_2:
            scheduled_time = calculate_post_time(slot2_today, schedule.variance_minutes)
        else:
            # Post tomorrow morning
            tomorrow = now.date() + timedelta(days=1)
            slot1_tomorrow = datetime.combine(tomorrow, schedule.time_slot_1)
            scheduled_time = calculate_post_time(slot1_tomorrow, schedule.variance_minutes)
        
        # Convert to UTC
        ist = pytz.timezone('Asia/Kolkata')
        return ist.localize(scheduled_time).astimezone(pytz.UTC).replace(tzinfo=None)
    else:
        return datetime.utcnow()

def get_next_story_slot(account_id):
    """Get next available 2-hour story slot"""
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    
    # Story slots: 6 AM, 8 AM, 10 AM, 12 PM, 2 PM, 4 PM, 6 PM, 8 PM, 10 PM, 12 AM, 2 AM (every 2 hours from 6 AM to 2 AM)
    story_hours = [6, 8, 10, 12, 14, 16, 18, 20, 22, 0, 2]
    
    current_hour = now.hour
    next_slot = None
    
    # Find next available slot today
    for hour in story_hours:
        if hour > current_hour:
            next_slot = datetime.combine(now.date(), datetime.min.time().replace(hour=hour))
            break
    
    # If no slot today, use first slot tomorrow
    if not next_slot:
        tomorrow = now.date() + timedelta(days=1)
        next_slot = datetime.combine(tomorrow, datetime.min.time().replace(hour=6))  # 6 AM tomorrow
    
    # Convert to UTC
    ist = pytz.timezone('Asia/Kolkata')
    return ist.localize(next_slot).astimezone(pytz.UTC).replace(tzinfo=None)

def queue_next_available_time(account_id, post_type='feed'):
    """Queue post for next available time based on daily limits"""
    today = datetime.utcnow().date()
    daily_count = Post.get_daily_post_count(account_id, today)
    
    if daily_count >= 25:
        # Queue for tomorrow
        tomorrow = today + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time().replace(hour=6))  # 6 AM next day
    else:
        # Schedule for next available slot today
        return get_next_available_slot(account_id)

def schedule_post_execution(post, schedule_type):
    """Schedule the post for execution"""
    if schedule_type == 'now':
        # Execute immediately
        execute_scheduled_post(post.id)
    else:
        # Schedule for later
        scheduler.add_job(
            func=execute_scheduled_post,
            trigger=DateTrigger(run_date=post.scheduled_time),
            args=[post.id],
            id=f'post_{post.id}',
            replace_existing=True
        )

@app.route('/posts')
def posts():
    """View all posts"""
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('posts.html', posts=posts)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

from flask import send_from_directory

@app.route('/api/post', methods=['POST'])
def api_post():
    """API endpoint for programmatic posting - supports Feed, Stories, and Carousels"""
    try:
        # Check if request is JSON or form data
        if request.is_json:
            data = request.get_json()
            files = None
        else:
            data = request.form.to_dict()
            files = request.files
        
        # Required fields
        account_id = data.get('account_id')
        post_type = data.get('post_type', 'feed').lower()
        
        if not account_id:
            return jsonify({'error': 'account_id is required'}), 400
        
        # Validate account
        account = Account.query.get(account_id)
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Handle different post types
        if post_type == 'feed':
            result = api_handle_feed_post(data, files, account)
        elif post_type == 'story':
            result = api_handle_story_post(data, files, account)
        elif post_type == 'carousel':
            result = api_handle_carousel_post(data, files, account)
        else:
            return jsonify({'error': 'Invalid post_type. Must be: feed, story, or carousel'}), 400
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message'),
                'post_id': result.get('post_id'),
                'scheduled_time': result.get('scheduled_time')
            }), 201
        else:
            return jsonify({'error': result.get('error')}), 400
            
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

def api_handle_feed_post(data, files, account):
    """Handle API feed post creation"""
    try:
        caption = data.get('caption', '')
        caption_template = data.get('caption_template', '')
        schedule_type = data.get('schedule_type', 'now')
        
        if not caption and not caption_template:
            return {'error': 'caption or caption_template is required'}
        
        # Handle file from API
        if files and 'file' in files:
            file = files['file']
        elif data.get('image_url'):
            # Handle external image URL
            return api_handle_external_image_post(data, account)
        else:
            return {'error': 'file upload or image_url is required'}
        
        # Save file
        saved_files = save_files_to_account_folder([file], account.id, 'feed')
        if not saved_files:
            return {'error': 'Failed to save uploaded file'}
        
        saved_file = saved_files[0]
        image_url = get_public_url_for_file(saved_file, account)
        if not image_url:
            return {'error': 'Failed to get public URL for image'}
        
        # Process caption
        if caption_template:
            final_caption = process_caption_template(caption_template, caption, account.username)
        else:
            final_caption = caption
        
        # Add hashtags if requested
        if data.get('include_hashtags', True):
            hashtags = get_random_hashtags(20)
            if hashtags:
                final_caption += '\n\n' + ' '.join(f'#{tag}' for tag in hashtags)
        
        # Calculate scheduled time
        scheduled_time = calculate_scheduled_time(schedule_type, account.id)
        
        # Create post
        post = Post(
            account_id=account.id,
            post_type='feed',
            content_type='image',
            caption=final_caption,
            media_urls=json.dumps([image_url]),
            media_files=json.dumps([saved_file['saved_name']]),
            scheduled_time=scheduled_time
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Schedule execution
        schedule_post_execution(post, schedule_type)
        
        return {
            'success': True,
            'message': 'Feed post created successfully',
            'post_id': post.id,
            'scheduled_time': scheduled_time.isoformat()
        }
        
    except Exception as e:
        return {'error': f'Error creating feed post: {str(e)}'}

def api_handle_story_post(data, files, account):
    """Handle API story post creation"""
    try:
        schedule_type = data.get('schedule_type', 'now')
        
        # Handle file from API
        if files and 'file' in files:
            file = files['file']
        elif data.get('image_url'):
            return api_handle_external_story_image(data, account)
        else:
            return {'error': 'file upload or image_url is required for story'}
        
        # Save file
        saved_files = save_files_to_account_folder([file], account.id, 'story')
        if not saved_files:
            return {'error': 'Failed to save story image'}
        
        saved_file = saved_files[0]
        image_url = get_public_url_for_file(saved_file, account)
        if not image_url:
            return {'error': 'Failed to get public URL for story image'}
        
        # Parse story elements
        story_elements = {}
        
        # Text overlay
        if data.get('text_overlay'):
            story_elements['text_overlay'] = {
                'text': data.get('text_overlay'),
                'position': data.get('text_position', 'center'),
                'style': data.get('text_style', 'default')
            }
        
        # Poll
        if data.get('poll_question'):
            poll_options = []
            for i in range(1, 5):
                option = data.get(f'poll_option_{i}')
                if option:
                    poll_options.append(option)
            
            if len(poll_options) >= 2:
                story_elements['poll'] = {
                    'question': data.get('poll_question'),
                    'options': poll_options
                }
        
        # Mentions
        mentions = data.get('mentions', [])
        if isinstance(mentions, str):
            mentions = [m.strip() for m in mentions.split(',') if m.strip()]
        if mentions:
            story_elements['mentions'] = mentions
        
        # Link
        if data.get('link_url'):
            story_elements['link'] = {
                'url': data.get('link_url'),
                'text': data.get('link_text', 'Swipe up')
            }
        
        # Calculate scheduled time
        scheduled_time = calculate_story_schedule_time(schedule_type, account.id)
        
        # Create post
        post = Post(
            account_id=account.id,
            post_type='story',
            content_type='story',
            caption='',
            media_urls=json.dumps([image_url]),
            media_files=json.dumps([saved_file['saved_name']]),
            story_elements=json.dumps(story_elements) if story_elements else None,
            scheduled_time=scheduled_time
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Schedule execution
        schedule_post_execution(post, schedule_type)
        
        return {
            'success': True,
            'message': 'Story created successfully',
            'post_id': post.id,
            'scheduled_time': scheduled_time.isoformat()
        }
        
    except Exception as e:
        return {'error': f'Error creating story: {str(e)}'}

def api_handle_carousel_post(data, files, account):
    """Handle API carousel post creation"""
    try:
        caption = data.get('caption', '')
        caption_template = data.get('caption_template', '')
        schedule_type = data.get('schedule_type', 'now')
        
        if not caption and not caption_template:
            return {'error': 'caption or caption_template is required for carousel'}
        
        # Handle multiple files from API
        if files:
            file_list = []
            for key in files.keys():
                if key.startswith('file'):
                    file_list.append(files[key])
            
            if not file_list:
                return {'error': 'No files found in request'}
        elif data.get('image_urls'):
            return api_handle_external_carousel_images(data, account)
        else:
            return {'error': 'file uploads or image_urls array is required for carousel'}
        
        if len(file_list) > 20:
            return {'error': 'Maximum 20 images allowed for carousel'}
        
        # Save files
        saved_files = save_files_to_account_folder(file_list, account.id, 'carousel')
        if not saved_files:
            return {'error': 'Failed to save carousel images'}
        
        # Get public URLs
        image_urls = []
        for saved_file in saved_files:
            image_url = get_public_url_for_file(saved_file, account)
            if not image_url:
                return {'error': f'Failed to get public URL for {saved_file["original_name"]}'}
            image_urls.append(image_url)
        
        # Process caption
        if caption_template:
            final_caption = process_caption_template(caption_template, caption, account.username)
        else:
            final_caption = caption
        
        # Add hashtags if requested
        if data.get('include_hashtags', True):
            hashtags = get_random_hashtags(20)
            if hashtags:
                final_caption += '\n\n' + ' '.join(f'#{tag}' for tag in hashtags)
        
        # Calculate scheduled time
        scheduled_time = calculate_scheduled_time(schedule_type, account.id)
        
        # Create post
        post = Post(
            account_id=account.id,
            post_type='carousel',
            content_type='carousel',
            caption=final_caption,
            media_urls=json.dumps(image_urls),
            media_files=json.dumps([f['saved_name'] for f in saved_files]),
            scheduled_time=scheduled_time
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Schedule execution
        schedule_post_execution(post, schedule_type)
        
        return {
            'success': True,
            'message': f'Carousel with {len(image_urls)} images created successfully',
            'post_id': post.id,
            'scheduled_time': scheduled_time.isoformat()
        }
        
    except Exception as e:
        return {'error': f'Error creating carousel: {str(e)}'}

def api_handle_external_image_post(data, account):
    """Handle external image URL for feed posts"""
    # For external URLs, we need to download and save the image
    # This is a placeholder - would need implementation based on requirements
    return {'error': 'External image URLs not yet implemented'}

def api_handle_external_story_image(data, account):
    """Handle external image URL for stories"""
    # For external URLs, we need to download and save the image
    # This is a placeholder - would need implementation based on requirements
    return {'error': 'External image URLs for stories not yet implemented'}

def api_handle_external_carousel_images(data, account):
    """Handle external image URLs for carousels"""
    # For external URLs, we need to download and save the images
    # This is a placeholder - would need implementation based on requirements
    return {'error': 'External image URLs for carousels not yet implemented'}

@app.route('/api/status/<int:post_id>')
def api_post_status(post_id):
    """Get status of a specific post"""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    return jsonify({
        'id': post.id,
        'post_type': post.post_type,
        'status': post.status,
        'scheduled_time': post.scheduled_time.isoformat() if post.scheduled_time else None,
        'actual_post_time': post.actual_post_time.isoformat() if post.actual_post_time else None,
        'instagram_post_id': post.instagram_post_id,
        'error_message': post.error_message,
        'account_username': post.account.username
    })

@app.route('/api/accounts')
def api_accounts():
    """List all active accounts"""
    accounts = Account.query.filter_by(is_active=True).all()
    
    return jsonify([{
        'id': account.id,
        'username': account.username,
        'instagram_id': account.instagram_id,
        'account_type': account.account_type,
        'niche': account.niche,
        'is_active': account.is_active
    } for account in accounts])

@app.route('/api/templates')
def api_templates():
    """List all caption templates"""
    templates = CaptionTemplate.query.filter_by(is_active=True).all()
    
    return jsonify([{
        'id': template.id,
        'name': template.name,
        'template': template.template,
        'category': template.category,
        'variables': json.loads(template.variables) if template.variables else []
    } for template in templates])

@app.route('/api/story-templates')
def api_story_templates():
    """List all story templates"""
    templates = StoryTemplate.query.all()
    
    return jsonify([{
        'id': template.id,
        'template_name': template.template_name,
        'template_type': template.template_type,
        'template_data': json.loads(template.template_data) if template.template_data else {}
    } for template in templates])

@app.route('/test_api')
def test_api():
    """Test route to check Instagram API functionality"""
    try:
        # Test basic API connectivity
        test_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        
        if not test_token:
            return jsonify({
                "status": "error",
                "message": "No Instagram access token found in environment variables"
            })
        
        # Test token validation
        token_valid, token_msg = instagram_api.validate_access_token(test_token)
        
        return jsonify({
            "status": "success",
            "instagram_api": "available",
            "token_validation": {
                "valid": token_valid,
                "message": token_msg
            },
            "base_url": instagram_api.base_url,
            "message": "Instagram API integration is working"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error testing API: {str(e)}"
        })

@app.route('/test_upload', methods=['GET', 'POST'])
def test_upload():
    """Test route for debugging file upload issues"""
    if request.method == 'POST':
        debug_info = {
            "form_data": dict(request.form),
            "files_keys": list(request.files.keys()),
            "content_type": request.content_type,
            "content_length": request.content_length
        }
        
        if 'file' in request.files:
            file = request.files['file']
            debug_info["file_info"] = {
                "filename": file.filename,
                "content_type": file.content_type,
                "has_content": bool(file.filename)
            }
        
        return jsonify({
            "status": "success",
            "message": "File upload test completed",
            "debug_info": debug_info
        })
    
    return '''
    <html>
    <body>
        <h2>File Upload Test</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept="image/*" required><br><br>
            <input type="text" name="test_field" placeholder="Test field"><br><br>
            <button type="submit">Test Upload</button>
        </form>
    </body>
    </html>
    '''

@app.route('/test_instagram_api', methods=['GET', 'POST'])
def test_instagram_api():
    """Test Instagram API with public image URL"""
    if request.method == 'POST':
        # Test with a public image URL to validate API request structure
        test_image_url = "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=800&h=800&fit=crop"
        test_caption = "Test post from Instagram automation tool"
        
        # Get test account
        test_account = Account.query.filter(Account.username.like('%test%')).first()
        if not test_account:
            return jsonify({
                "status": "error",
                "message": "No test account found. Please create a test account first."
            })
        
        print(f"\n=== TESTING INSTAGRAM API WITH PUBLIC IMAGE ===")
        print(f"Test account: {test_account.username}")
        print(f"Test image URL: {test_image_url}")
        
        # Test the API call
        result = instagram_api.upload_media(
            test_account.instagram_id,
            test_image_url,
            test_caption,
            test_account.access_token
        )
        
        return jsonify({
            "status": "success" if 'id' in result else "error",
            "message": "API test completed",
            "result": result,
            "account_used": test_account.username
        })
    
    return '''
    <html>
    <body>
        <h2>Instagram API Test</h2>
        <p>This will test the Instagram API using a public image URL to validate the request structure.</p>
        <form method="POST">
            <button type="submit">Test Instagram API</button>
        </form>
        <br>
        <p><strong>Note:</strong> This test uses a public image URL from Unsplash to validate that our API request structure is correct.</p>
    </body>
    </html>
    '''

@app.route('/setup_help')
def setup_help():
    """Help page for setting up public URLs"""
    ngrok_url = detect_ngrok_url()
    ngrok_status = "✅ DETECTED" if ngrok_url else "❌ NOT DETECTED"
    
    # Get GCS status
    gcs_status = gcs.get_status()
    gcs_overall_status = "✅ READY" if gcs_status['authenticated'] and gcs_status['bucket_exists'] else "❌ NOT READY"
    
    accounts = Account.query.all()
    real_accounts = [acc for acc in accounts if not acc.access_token.startswith('test')]
    test_accounts = [acc for acc in accounts if acc.access_token.startswith('test')]
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Setup Help - Instagram Automation</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .success {{ background-color: #d4edda; border: 1px solid #c3e6cb; }}
            .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; }}
            .error {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
            .code {{ background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-family: monospace; }}
            .account {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>🛠️ Instagram Automation Setup Help</h1>
        
                 <h2>📊 Current Status</h2>
         
         <div class="status {'success' if gcs_status['authenticated'] and gcs_status['bucket_exists'] else 'error'}">
             <strong>Google Cloud Storage:</strong> {gcs_overall_status}<br>
             <strong>Available:</strong> {'✅ Yes' if gcs_status['available'] else '❌ No'}<br>
             <strong>Authenticated:</strong> {'✅ Yes' if gcs_status['authenticated'] else '❌ No'}<br>
             <strong>Bucket:</strong> {gcs_status['bucket_name']}<br>
             <strong>Bucket Exists:</strong> {'✅ Yes' if gcs_status['bucket_exists'] else '❌ No'}<br>
             <strong>Project ID:</strong> {gcs_status['project_id'] or 'Not configured'}
         </div>
         
         <div class="status {'success' if ngrok_url else 'warning'}">
             <strong>Ngrok Status:</strong> {ngrok_status}<br>
             {'<strong>Public URL:</strong> ' + ngrok_url if ngrok_url else 'No ngrok tunnel detected'}
         </div>
        
        <h2>👥 Account Summary</h2>
        <div class="status {'success' if test_accounts else 'warning'}">
            <strong>Test Accounts:</strong> {len(test_accounts)}<br>
            {'✅ Can upload immediately (mock Instagram API)' if test_accounts else '⚠️ No test accounts found'}
        </div>
        
                 <div class="status {'success' if not real_accounts or (gcs_status['authenticated'] and gcs_status['bucket_exists']) or ngrok_url else 'error'}">
             <strong>Real Instagram Accounts:</strong> {len(real_accounts)}<br>
             {('✅ Ready to upload (GCS or ngrok available)' if (gcs_status['authenticated'] and gcs_status['bucket_exists']) or ngrok_url else '❌ Require public URL for uploads') if real_accounts else 'ℹ️ No real accounts configured'}
         </div>
        
                 <h2>🚀 Quick Setup Options</h2>
         
         <h3>Option 1: Google Cloud Storage (Recommended for Production)</h3>
         <div class="code">
             # 1. Create GCS Bucket<br>
             gcloud auth login<br>
             gsutil mb gs://{gcs_status['bucket_name']}<br>
             gsutil iam ch allUsers:objectViewer gs://{gcs_status['bucket_name']}<br><br>
             
             # 2. Set up authentication<br>
             gcloud auth application-default login<br>
             # OR create service account key and set path in .env<br><br>
             
             # 3. Update .env file<br>
             GCS_PROJECT_ID=your-project-id<br>
             GCS_BUCKET_NAME={gcs_status['bucket_name']}<br>
             # GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json (optional)<br><br>
             
             # 4. Restart the application<br>
             # Images will automatically upload to GCS for real accounts
         </div>
         
         <h3>Option 2: Use Test Account (Recommended for Development)</h3>
        <div class="code">
            1. Go to Add Account: <a href="/add_account">http://localhost:5555/add_account</a><br>
            2. Username: test_myaccount<br>
            3. Instagram ID: test123456<br>
            4. Access Token: test_token<br>
            5. Upload works immediately (no real Instagram API calls)
        </div>
        
                 <h3>Option 3: Setup Ngrok (Alternative for Testing)</h3>
         <div class="code">
             # Install ngrok<br>
             brew install ngrok  # Mac<br>
             # or download from https://ngrok.com<br><br>
             
             # Run ngrok in a new terminal<br>
             ngrok http 5555<br><br>
             
             # Copy the https URL (e.g., https://abc123.ngrok.io)<br>
             # Set environment variable (optional):<br>
             export NGROK_URL=https://abc123.ngrok.io<br><br>
             
             # Restart this app - it will auto-detect ngrok
         </div>
        
        <h2>📋 Troubleshooting</h2>
        
        <h3>❌ "Instagram cannot access localhost URLs"</h3>
        <p><strong>Solution:</strong> Use ngrok or test accounts. Instagram's servers cannot reach your localhost.</p>
        
        <h3>❌ "Only photo or video can be accepted as media type"</h3>
        <p><strong>Cause:</strong> Instagram couldn't fetch the image from the URL.</p>
        <p><strong>Solution:</strong> Ensure URL is publicly accessible (use ngrok or cloud storage).</p>
        
        <h3>❌ "Invalid OAuth access token"</h3>
        <p><strong>Cause:</strong> Using test token with real Instagram API.</p>
        <p><strong>Solution:</strong> Use proper Instagram Graph API token or switch to test account.</p>
        
        <div style="margin-top: 40px; text-align: center;">
            <a href="/" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                ← Back to Dashboard
            </a>
        </div>
    </body>
    </html>
    '''

@app.route('/init_db')
def init_db():
    """Initialize database with sample data"""
    try:
        db.create_all()
        
        # Add sample hashtags
        if HashtagRepository.query.count() == 0:
            sample_hashtags = [
                ('motivation', 'General'), ('inspiration', 'General'), ('success', 'General'),
                ('entrepreneurship', 'Business'), ('business', 'Business'), ('startup', 'Business'),
                ('lifestyle', 'Lifestyle'), ('wellness', 'Lifestyle'), ('mindfulness', 'Lifestyle'),
                ('growth', 'Personal'), ('goals', 'Personal'), ('mindset', 'Personal'),
                ('monday', 'Daily'), ('tuesday', 'Daily'), ('wednesday', 'Daily'),
                ('thursday', 'Daily'), ('friday', 'Daily'), ('weekend', 'Daily'),
                ('love', 'Engagement'), ('follow', 'Engagement'), ('like', 'Engagement'),
                ('comment', 'Engagement'), ('share', 'Engagement'), ('tag', 'Engagement')
            ]
            
            for hashtag, category in sample_hashtags:
                tag = HashtagRepository(hashtag=hashtag, category=category)
                db.session.add(tag)
        
        # Add sample caption templates
        if CaptionTemplate.query.count() == 0:
            sample_templates = [
                {
                    'name': 'Motivational Monday',
                    'template': 'Good {time_period} from {account_name}! 🌟\n\n{custom_text}\n\nWhat\'s your motivation for this {day_of_week}? Tell us in the comments! 👇',
                    'category': 'Motivational'
                },
                {
                    'name': 'Daily Inspiration',
                    'template': 'Happy {day_of_week}, everyone! ✨\n\n{custom_text}\n\nRemember: Every day is a new opportunity to grow! 🚀',
                    'category': 'Inspirational'
                },
                {
                    'name': 'Business Tips',
                    'template': '{account_name} here with your {day_of_week} business tip! 💼\n\n{custom_text}\n\nWhat challenges are you facing in your business? Let\'s discuss! 💬',
                    'category': 'Business'
                }
            ]
            
            for template_data in sample_templates:
                template = CaptionTemplate(
                    name=template_data['name'],
                    template=template_data['template'],
                    category=template_data['category']
                )
                db.session.add(template)
        
        db.session.commit()
        flash('Database initialized successfully!', 'success')
        
    except Exception as e:
        flash(f'Error initializing database: {str(e)}', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000) 