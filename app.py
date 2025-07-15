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
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
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

# Add PIL import for text-based story generation
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available for text story generation. Install with: pip install Pillow")

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
    content_type = db.Column(db.String(50), nullable=False)  # 'image', 'carousel', 'story'
    caption = db.Column(db.Text)
    media_urls = db.Column(db.Text)  # JSON array of image URLs
    hashtags = db.Column(db.Text)  # JSON array of hashtags
    scheduled_time = db.Column(db.DateTime, nullable=False)
    actual_post_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='scheduled')  # 'scheduled', 'posted', 'failed', 'cancelled'
    instagram_post_id = db.Column(db.String(255))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

    def create_text_story_image(self, text, width=1080, height=1920):
        """Create a text-based story image"""
        if not PIL_AVAILABLE:
            return None, "PIL not available for text story generation"
        
        # Create a new image with gradient background
        img = Image.new('RGB', (width, height), color='#4A90E2')
        draw = ImageDraw.Draw(img)
        
        # Add gradient effect (simple)
        for y in range(height):
            alpha = int(255 * (y / height))
            color = (74, 144, 226, alpha)  # Blue gradient
            draw.line([(0, y), (width, y)], fill=(74 + alpha//4, 144 + alpha//8, 226))
        
        # Try to use a nice font, fallback to default
        try:
            # Try to use system fonts
            font_size = 80
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            except:
                font = ImageFont.load_default()
        
        # Calculate text position (centered)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Handle multi-line text
        lines = text.split('\n')
        if len(lines) == 1 and text_width > width - 100:
            # Auto-wrap long text
            words = text.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_bbox = draw.textbbox((0, 0), test_line, font=font)
                if test_bbox[2] - test_bbox[0] <= width - 100:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
        
        # Calculate total text height for all lines
        total_height = len(lines) * (text_height + 20)
        start_y = (height - total_height) // 2
        
        # Draw text with shadow effect
        for i, line in enumerate(lines):
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            x = (width - line_width) // 2
            y = start_y + i * (text_height + 20)
            
            # Draw shadow
            draw.text((x + 3, y + 3), line, font=font, fill='black')
            # Draw main text
            draw.text((x, y), line, font=font, fill='white')
        
        # Save to temporary file
        temp_filename = f"story_text_{int(time.time())}.png"
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        img.save(temp_path, 'PNG')
        
        return temp_path, None

    def upload_story(self, account_id, image_url, access_token=None):
        """Upload story to Instagram (create story container)"""
        token = access_token or self.default_token
        url = f"{self.base_url}/{account_id}/media"
        
        print(f"\n=== INSTAGRAM STORY UPLOAD ===")
        print(f"API URL: {url}")
        print(f"Account ID: {account_id}")
        print(f"Image URL: {image_url}")
        print(f"Access token (first 20 chars): {token[:20] if token else 'None'}...")
        
        # Validate inputs
        if not image_url:
            return {"error": "Image URL is required for story"}
            
        if not image_url.startswith(('http://', 'https://')):
            return {"error": "Image URL must be a valid HTTP/HTTPS URL accessible by Instagram"}
        
        # Prepare request data for story
        data = {
            'image_url': image_url,
            'media_type': 'STORIES',  # This is the key difference for stories
            'access_token': token
        }
        
        print(f"Story request data: {data}")
        
        try:
            response = requests.post(url, data=data, timeout=30)
            
            print(f"Instagram Story API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if 'id' in result:
                    print(f"SUCCESS: Story container created with ID: {result['id']}")
                    return result
                else:
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    print(f"ERROR: Story API success but no ID - {error_msg}")
                    return {"error": f"Instagram Story API error: {error_msg}"}
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                    print(f"ERROR: Story API failed with message: {error_message}")
                except:
                    error_message = f"HTTP {response.status_code}: {response.text}"
                
                return {"error": f"Failed to upload story: {error_message}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error during story upload: {str(e)}"}

    def post_story_to_instagram(self, account_id, image_url, text=None, access_token=None):
        """Complete flow: upload and publish story to Instagram"""
        
        # Check if this is a test account
        if access_token and access_token.startswith('test'):
            print(f"\n=== TEST STORY ACCOUNT DETECTED ===")
            print(f"Account ID: {account_id}")
            print(f"Image URL: {image_url}")
            print(f"Text: {text}")
            print(f"Skipping actual Instagram API call for test account")
            
            # Return success for test accounts
            return {
                "id": f"test_story_{account_id}_{int(time.time())}",
                "message": "Test story created successfully (no actual Instagram API call)"
            }
        
        # Step 1: Upload story (create container)
        upload_result = self.upload_story(account_id, image_url, access_token)
        
        if not upload_result:
            return {"error": "Failed to upload story - no response from Instagram"}
        
        if 'error' in upload_result:
            return {"error": f"Story upload failed: {upload_result['error']}"}
        
        if 'id' not in upload_result:
            return {"error": "Story upload failed - no container ID returned"}
        
        # Step 2: Publish story
        publish_result = self.publish_media(account_id, upload_result['id'], access_token)
        
        if not publish_result:
            return {"error": "Failed to publish story - no response from Instagram"}
        
        if 'error' in publish_result:
            return {"error": f"Story publish failed: {publish_result['error']}"}
        
        return publish_result

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
            
            # For now, use first image (single post)
            image_url = media_urls[0]
            
            # Post to Instagram
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
    """Upload and schedule posts"""
    if request.method == 'POST':
        try:
            # Debug logging
            print(f"Upload POST request received")
            print(f"Content-Type: {request.content_type}")
            print(f"Content-Length: {request.content_length}")
            print(f"Form data: {dict(request.form)}")
            print(f"Files in request: {list(request.files.keys())}")
            
            # Additional debugging for file upload
            if 'file' in request.files:
                file_obj = request.files['file']
                print(f"File object found: {file_obj}")
                print(f"File filename: {file_obj.filename}")
                print(f"File content type: {file_obj.content_type}")
                print(f"File has content: {bool(file_obj.filename)}")
            else:
                print("No 'file' key in request.files")
                print(f"All files keys: {list(request.files.keys())}")
                print(f"Raw form data: {request.form}")
                
            # Get form data with validation
            account_id = request.form.get('account_id')
            caption_template = request.form.get('caption_template', '')
            custom_text = request.form.get('custom_text', '')
            schedule_type = request.form.get('schedule_type', 'now')
            
            # Validate account selection
            if not account_id:
                flash('Please select an Instagram account', 'error')
                # Return to form with existing accounts and templates
                accounts = Account.query.filter_by(is_active=True).all()
                templates = CaptionTemplate.query.filter_by(is_active=True).all()
                return render_template('upload.html', accounts=accounts, templates=templates)
            
            # Validate caption content
            if not custom_text.strip() and not caption_template:
                flash('Please enter caption text or select a template', 'error')
                accounts = Account.query.filter_by(is_active=True).all()
                templates = CaptionTemplate.query.filter_by(is_active=True).all()
                return render_template('upload.html', accounts=accounts, templates=templates)
            
            # Handle file upload with detailed error messages
            if 'file' not in request.files:
                flash('No file was uploaded. Please select an image file.', 'error')
                print("Error: 'file' not in request.files")
                accounts = Account.query.filter_by(is_active=True).all()
                templates = CaptionTemplate.query.filter_by(is_active=True).all()
                return render_template('upload.html', accounts=accounts, templates=templates)
            
            file = request.files['file']
            print(f"File object: {file}")
            print(f"File filename: {file.filename}")
            print(f"File content type: {file.content_type}")
            
            if not file or file.filename == '':
                flash('No file was selected. Please choose an image file.', 'error')
                print("Error: File is empty or no filename")
                accounts = Account.query.filter_by(is_active=True).all()
                templates = CaptionTemplate.query.filter_by(is_active=True).all()
                return render_template('upload.html', accounts=accounts, templates=templates)
            
            if file:
                # Save file
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Log the URL issue for debugging
                print(f"\n=== FILE UPLOAD DEBUG ===")
                print(f"Saved file: {filename}")
                print(f"File path: {file_path}")
                
                # Check if we're using a test account or real account
                account = Account.query.get(account_id)
                if not account:
                    flash('Account not found', 'error')
                    accounts = Account.query.filter_by(is_active=True).all()
                    templates = CaptionTemplate.query.filter_by(is_active=True).all()
                    return render_template('upload.html', accounts=accounts, templates=templates)
                
                is_test_account = account.access_token.startswith('test')
                
                if is_test_account:
                    # For test accounts, use localhost URL (will be handled by test account logic)
                    image_url = f"http://localhost:5555/uploads/{filename}"
                    print(f"Test account detected - using localhost URL: {image_url}")
                else:
                    # For real accounts, try Google Cloud Storage first, then ngrok
                    print(f"Real Instagram account detected: @{account.username}")
                    print(f"Account token: {account.access_token[:20]}...")
                    
                    image_url = None
                    upload_method = None
                    
                    # Option 1: Try Google Cloud Storage
                    if gcs.is_available():
                        print(f"Attempting upload to Google Cloud Storage...")
                        
                        # Re-open the file for GCS upload
                        try:
                            with open(file_path, 'rb') as gcs_file:
                                public_url, gcs_error = gcs.upload_file(
                                    gcs_file, 
                                    filename, 
                                    file.content_type
                                )
                                
                            if public_url:
                                image_url = public_url
                                upload_method = "Google Cloud Storage"
                                print(f"✅ SUCCESS: Using GCS URL: {image_url}")
                            else:
                                print(f"❌ GCS upload failed: {gcs_error}")
                                
                        except Exception as e:
                            print(f"❌ GCS upload error: {e}")
                    
                    # Option 2: Fallback to ngrok if GCS is not available
                    if not image_url:
                        print(f"Trying ngrok fallback...")
                        ngrok_url = detect_ngrok_url()
                        if ngrok_url:
                            image_url = f"{ngrok_url}/uploads/{filename}"
                            upload_method = "ngrok"
                            print(f"✅ SUCCESS: Using ngrok URL: {image_url}")
                    
                    # Option 3: No public URL available - provide helpful error
                    if not image_url:
                        gcs_status = gcs.get_status()
                        
                        error_msg = f"""
🚨 REAL INSTAGRAM ACCOUNT - PUBLIC URL REQUIRED 🚨

Current account: @{account.username} (Real Instagram account)

📊 CURRENT STATUS:
• Google Cloud Storage: {'✅ Available' if gcs_status['available'] else '❌ Not Available'}
• GCS Authentication: {'✅ Authenticated' if gcs_status['authenticated'] else '❌ Not Authenticated'}
• GCS Bucket: {'✅ Exists' if gcs_status['bucket_exists'] else '❌ Missing/Inaccessible'}
• Ngrok: {'✅ Detected' if detect_ngrok_url() else '❌ Not Running'}

🛠️ SETUP GOOGLE CLOUD STORAGE (Recommended):

1. **Create GCS Bucket:**
   - Go to Google Cloud Console
   - Create a new bucket: '{gcs_status['bucket_name']}'
   - Set public access policies

2. **Authentication Setup:**
   - Create service account key OR
   - Run: gcloud auth application-default login

3. **Update Configuration:**
   - Set GCS_PROJECT_ID in .env file
   - Set GCS_BUCKET_NAME in .env file
   - Restart the application

🔧 ALTERNATIVE OPTIONS:
• Use test account (username starting with 'test_')
• Setup ngrok: ngrok http 5555
• Use different image hosting service

📋 Need help? Visit /setup_help for detailed instructions.
                        """
                        
                        flash(error_msg, 'error')
                        accounts = Account.query.filter_by(is_active=True).all()
                        templates = CaptionTemplate.query.filter_by(is_active=True).all()
                        return render_template('upload.html', accounts=accounts, templates=templates)
                    
                    print(f"✅ Using {upload_method} for image hosting")
                
                print(f"Final image URL: {image_url}")
                
                # Account was already retrieved above - no need to get it again
                
                # Process caption
                if caption_template:
                    caption = process_caption_template(caption_template, custom_text, account.username)
                else:
                    caption = custom_text
                
                # Add hashtags
                hashtags = get_random_hashtags(20)
                if hashtags:
                    caption += '\n\n' + ' '.join(f'#{tag}' for tag in hashtags)
                
                # Determine scheduled time
                if schedule_type == 'now':
                    scheduled_time = datetime.utcnow()
                elif schedule_type == 'next_slot':
                    # Get next available time slot
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
                        scheduled_time = ist.localize(scheduled_time).astimezone(pytz.UTC).replace(tzinfo=None)
                    else:
                        scheduled_time = datetime.utcnow()
                else:
                    scheduled_time = datetime.utcnow()
                
                # Create post record
                post = Post(
                    account_id=account_id,
                    content_type='image',
                    caption=caption,
                    media_urls=json.dumps([image_url]),
                    scheduled_time=scheduled_time
                )
                
                db.session.add(post)
                db.session.commit()
                
                # Schedule the post
                if schedule_type == 'now':
                    # Execute immediately
                    execute_scheduled_post(post.id)
                else:
                    # Schedule for later
                    scheduler.add_job(
                        func=execute_scheduled_post,
                        trigger=DateTrigger(run_date=scheduled_time),
                        args=[post.id],
                        id=f'post_{post.id}',
                        replace_existing=True
                    )
                
                flash('Post scheduled successfully!', 'success')
                return redirect(url_for('posts'))
            
        except Exception as e:
            flash(f'Error uploading post: {str(e)}', 'error')
            return redirect(url_for('upload'))
    
    # GET request - show upload form
    accounts = Account.query.filter_by(is_active=True).all()
    templates = CaptionTemplate.query.filter_by(is_active=True).all()
    
    return render_template('upload.html', accounts=accounts, templates=templates)

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

@app.route('/post_story', methods=['GET', 'POST'])
def post_story():
    """Post a text-based story to Instagram"""
    if request.method == 'POST':
        try:
            # Get form data
            account_id = request.form.get('account_id')
            story_text = request.form.get('story_text', 'This is a Story')
            
            # Validate inputs
            if not account_id:
                return jsonify({
                    "status": "error",
                    "message": "Please select an Instagram account"
                })
            
            if not story_text.strip():
                return jsonify({
                    "status": "error", 
                    "message": "Story text is required"
                })
            
            # Get account
            account = Account.query.get(account_id)
            if not account or not account.is_active:
                return jsonify({
                    "status": "error",
                    "message": "Account not found or inactive"
                })
            
            print(f"\n=== POSTING STORY ===")
            print(f"Account: @{account.username}")
            print(f"Story Text: {story_text}")
            
            # Step 1: Create text-based story image
            temp_image_path, error = instagram_api.create_text_story_image(story_text)
            
            if error:
                return jsonify({
                    "status": "error",
                    "message": f"Failed to create story image: {error}"
                })
            
            # Step 2: Get public URL for the image
            image_url = None
            
            # Check if this is a test account
            is_test_account = account.access_token and account.access_token.startswith('test')
            
            if is_test_account:
                # For test accounts, use localhost URL
                filename = os.path.basename(temp_image_path)
                image_url = f"http://localhost:5555/uploads/{filename}"
                print(f"Test account - using localhost URL: {image_url}")
            else:
                # For real accounts, try to get public URL
                # Try Google Cloud Storage first
                gcs = GoogleCloudStorage()
                if gcs.is_available():
                    try:
                        with open(temp_image_path, 'rb') as f:
                            filename = os.path.basename(temp_image_path)
                            public_url, gcs_error = gcs.upload_file(f, filename, 'image/png')
                            
                        if public_url:
                            image_url = public_url
                            print(f"Using GCS URL: {image_url}")
                        else:
                            print(f"GCS upload failed: {gcs_error}")
                    except Exception as e:
                        print(f"GCS upload error: {e}")
                
                # If GCS failed, return error for real accounts
                if not image_url:
                    return jsonify({
                        "status": "error",
                        "message": "Failed to upload story image to cloud storage. Please ensure Google Cloud Storage is configured."
                    })
            
            # Step 3: Post story to Instagram
            result = instagram_api.post_story_to_instagram(
                account.instagram_id,
                image_url,
                story_text,
                account.access_token
            )
            
            # Step 4: Clean up temporary file
            try:
                os.remove(temp_image_path)
            except:
                pass
            
            # Step 5: Save to database
            if result and 'id' in result:
                post = Post(
                    account_id=account_id,
                    content_type='story',
                    caption=story_text,
                    media_urls=json.dumps([image_url]),
                    scheduled_time=datetime.utcnow(),
                    actual_post_time=datetime.utcnow(),
                    status='posted',
                    instagram_post_id=result['id']
                )
                db.session.add(post)
                db.session.commit()
                
                return jsonify({
                    "status": "success",
                    "message": f"Story posted successfully to @{account.username}!",
                    "instagram_id": result['id'],
                    "account": account.username
                })
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No response'
                return jsonify({
                    "status": "error",
                    "message": f"Failed to post story: {error_msg}"
                })
                
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error posting story: {str(e)}"
            })
    
    # GET request - show story form
    accounts = Account.query.filter_by(is_active=True).all()
    
    return '''
    <html>
    <head>
        <title>Post Instagram Story</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            select, textarea, button { width: 100%; padding: 10px; font-size: 16px; }
            textarea { height: 100px; resize: vertical; }
            button { background: #4A90E2; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #357ABD; }
            .result { margin-top: 20px; padding: 15px; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <h1>📱 Post Instagram Story</h1>
        <p>Create a text-based story with beautiful gradient background</p>
        
        <form id="storyForm">
            <div class="form-group">
                <label for="account_id">Select Instagram Account:</label>
                <select id="account_id" name="account_id" required>
                    <option value="">Choose an account...</option>
                    ''' + ''.join([f'<option value="{acc.id}">@{acc.username} ({acc.niche or "General"})</option>' for acc in accounts]) + '''
                </select>
            </div>
            
            <div class="form-group">
                <label for="story_text">Story Text:</label>
                <textarea id="story_text" name="story_text" placeholder="This is a Story" required>This is a Story</textarea>
            </div>
            
            <button type="submit">📱 Post Story</button>
        </form>
        
        <div id="result"></div>
        
        <script>
            document.getElementById('storyForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const button = document.querySelector('button[type="submit"]');
                const resultDiv = document.getElementById('result');
                
                button.textContent = '⏳ Posting Story...';
                button.disabled = true;
                
                const formData = new FormData(this);
                
                fetch('/post_story', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resultDiv.innerHTML = `<div class="result success">✅ ${data.message}</div>`;
                    } else {
                        resultDiv.innerHTML = `<div class="result error">❌ ${data.message}</div>`;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = `<div class="result error">❌ Error: ${error.message}</div>`;
                })
                .finally(() => {
                    button.textContent = '📱 Post Story';
                    button.disabled = false;
                });
            });
        </script>
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

@app.route('/bulk_accounts', methods=['GET', 'POST'])
def bulk_accounts():
    """Bulk account creation for load testing"""
    if request.method == 'POST':
        try:
            # Get form data
            account_count = int(request.form.get('account_count', 100))
            account_type = request.form.get('account_type', 'test')
            real_percentage = int(request.form.get('real_percentage', 10))
            
            # Validate inputs
            if account_count < 1 or account_count > 1000:
                flash('Account count must be between 1 and 1000', 'error')
                return render_template('bulk_accounts.html')
            
            if real_percentage < 0 or real_percentage > 100:
                flash('Real account percentage must be between 0 and 100', 'error')
                return render_template('bulk_accounts.html')
            
            # Import test account generator
            import sys
            sys.path.append('.')
            from test_account_generator import TestAccountGenerator
            
            # Generate accounts
            generator = TestAccountGenerator()
            accounts = generator.generate_mixed_accounts(account_count, real_percentage)
            
            # Insert into database
            created_count = 0
            for account_data in accounts:
                try:
                    # Check if account already exists
                    existing = Account.query.filter_by(username=account_data['username']).first()
                    if existing:
                        continue
                    
                    # Create new account
                    account = Account(
                        username=account_data['username'],
                        instagram_id=account_data['instagram_id'],
                        access_token=account_data['access_token'],
                        account_type=account_data['account_type'],
                        niche=account_data['niche'],
                        is_active=account_data['is_active']
                    )
                    
                    db.session.add(account)
                    created_count += 1
                    
                except Exception as e:
                    print(f"Error creating account {account_data['username']}: {e}")
                    continue
            
            # Commit all accounts
            db.session.commit()
            
            # Create default posting schedules for new accounts
            new_accounts = Account.query.filter(
                Account.username.like('%test_%')
            ).all()
            
            schedule_count = 0
            for account in new_accounts:
                existing_schedule = PostingSchedule.query.filter_by(account_id=account.id).first()
                if not existing_schedule:
                    schedule = PostingSchedule(
                        account_id=account.id,
                        time_slot_1=datetime.strptime('13:00', '%H:%M').time(),
                        time_slot_2=datetime.strptime('22:00', '%H:%M').time(),
                        variance_minutes=15
                    )
                    db.session.add(schedule)
                    schedule_count += 1
            
            db.session.commit()
            
            flash(f'Successfully created {created_count} accounts and {schedule_count} schedules!', 'success')
            return redirect(url_for('load_test_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating bulk accounts: {str(e)}', 'error')
            return render_template('bulk_accounts.html')
    
    # GET request - show bulk creation form
    return render_template('bulk_accounts.html')

@app.route('/load_test_dashboard')
def load_test_dashboard():
    """Load testing dashboard"""
    # Get account statistics
    total_accounts = Account.query.count()
    test_accounts = Account.query.filter(Account.access_token.like('test_%')).count()
    real_accounts = total_accounts - test_accounts
    active_accounts = Account.query.filter_by(is_active=True).count()
    
    # Get posting statistics
    total_posts = Post.query.count()
    scheduled_posts = Post.query.filter_by(status='scheduled').count()
    posted_posts = Post.query.filter_by(status='posted').count()
    failed_posts = Post.query.filter_by(status='failed').count()
    
    # Get recent activity
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
    
    # Calculate performance metrics
    success_rate = (posted_posts / total_posts * 100) if total_posts > 0 else 0
    
    # Get database performance info
    import psutil
    import os
    
    # System performance
    cpu_percent = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    disk_info = psutil.disk_usage('/')
    
    # Database file size (SQLite)
    db_file_path = 'instagram_automation.db'
    db_size = os.path.getsize(db_file_path) / (1024 * 1024) if os.path.exists(db_file_path) else 0
    
    performance_metrics = {
        'cpu_percent': cpu_percent,
        'memory_percent': memory_info.percent,
        'memory_used_gb': memory_info.used / (1024**3),
        'memory_total_gb': memory_info.total / (1024**3),
        'disk_percent': disk_info.percent,
        'disk_used_gb': disk_info.used / (1024**3),
        'disk_total_gb': disk_info.total / (1024**3),
        'db_size_mb': db_size
    }
    
    return render_template('load_test_dashboard.html', 
                         total_accounts=total_accounts,
                         test_accounts=test_accounts,
                         real_accounts=real_accounts,
                         active_accounts=active_accounts,
                         total_posts=total_posts,
                         scheduled_posts=scheduled_posts,
                         posted_posts=posted_posts,
                         failed_posts=failed_posts,
                         success_rate=success_rate,
                         recent_posts=recent_posts,
                         performance_metrics=performance_metrics)

@app.route('/stress_test', methods=['GET', 'POST'])
def stress_test():
    """Stress test with concurrent posting"""
    if request.method == 'POST':
        try:
            # Get test parameters
            account_count = int(request.form.get('account_count', 10))
            posts_per_account = int(request.form.get('posts_per_account', 1))
            concurrent_posts = int(request.form.get('concurrent_posts', 5))
            test_duration = int(request.form.get('test_duration', 60))  # seconds
            
            # Validate parameters
            if account_count > 100:
                flash('Account count limited to 100 for stress testing', 'error')
                return render_template('stress_test.html')
            
            # Get test accounts
            test_accounts = Account.query.filter(
                Account.access_token.like('test_%')
            ).filter_by(is_active=True).limit(account_count).all()
            
            if len(test_accounts) < account_count:
                flash(f'Only {len(test_accounts)} test accounts available. Create more test accounts first.', 'error')
                return render_template('stress_test.html')
            
            # Create stress test posts
            import threading
            import time
            from datetime import datetime, timedelta
            
            posts_created = 0
            errors = []
            
            def create_test_post(account, post_num):
                try:
                    # Create a test post
                    post = Post(
                        account_id=account.id,
                        content_type='image',
                        caption=f'Stress test post #{post_num} from {account.username}',
                        media_urls=json.dumps(['http://localhost:5555/static/test_image.jpg']),
                        scheduled_time=datetime.utcnow() + timedelta(seconds=random.randint(1, 60))
                    )
                    
                    db.session.add(post)
                    db.session.commit()
                    return True
                except Exception as e:
                    errors.append(f"Error creating post for {account.username}: {e}")
                    return False
            
            # Execute stress test
            start_time = time.time()
            threads = []
            
            for account in test_accounts:
                for i in range(posts_per_account):
                    thread = threading.Thread(
                        target=create_test_post,
                        args=(account, i + 1)
                    )
                    threads.append(thread)
                    thread.start()
                    
                    # Limit concurrent threads
                    if len(threads) >= concurrent_posts:
                        for t in threads:
                            t.join()
                        threads = []
                    
                    # Small delay to prevent overwhelming the system
                    time.sleep(0.1)
            
            # Wait for remaining threads
            for t in threads:
                t.join()
            
            end_time = time.time()
            test_duration_actual = end_time - start_time
            
            # Calculate results
            total_posts_attempted = account_count * posts_per_account
            posts_created = Post.query.filter(
                Post.created_at >= datetime.utcnow() - timedelta(seconds=test_duration_actual + 10)
            ).count()
            
            success_rate = (posts_created / total_posts_attempted * 100) if total_posts_attempted > 0 else 0
            
            # Flash results
            flash(f'Stress test completed! Created {posts_created}/{total_posts_attempted} posts ({success_rate:.1f}% success rate) in {test_duration_actual:.1f} seconds', 'success')
            
            if errors:
                flash(f'Encountered {len(errors)} errors during stress test', 'warning')
            
            return redirect(url_for('load_test_dashboard'))
            
        except Exception as e:
            flash(f'Stress test failed: {str(e)}', 'error')
            return render_template('stress_test.html')
    
    # GET request - show stress test form
    test_accounts_count = Account.query.filter(Account.access_token.like('test_%')).count()
    return render_template('stress_test.html', test_accounts_count=test_accounts_count)

@app.route('/api/performance_metrics')
def performance_metrics():
    """API endpoint for real-time performance metrics"""
    try:
        import psutil
        import os
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()
        
        # Database metrics
        db_file_path = 'instagram_automation.db'
        db_size = os.path.getsize(db_file_path) / (1024 * 1024) if os.path.exists(db_file_path) else 0
        
        # Application metrics
        total_accounts = Account.query.count()
        active_posts = Post.query.filter_by(status='scheduled').count()
        failed_posts = Post.query.filter_by(status='failed').count()
        
        # Background job metrics (approximation)
        pending_jobs = Post.query.filter_by(status='scheduled').filter(
            Post.scheduled_time <= datetime.utcnow() + timedelta(hours=1)
        ).count()
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_info.percent,
                'memory_used_mb': memory_info.used / (1024**2),
                'memory_available_mb': memory_info.available / (1024**2)
            },
            'database': {
                'size_mb': db_size,
                'total_accounts': total_accounts,
                'active_posts': active_posts,
                'failed_posts': failed_posts
            },
            'application': {
                'pending_jobs': pending_jobs,
                'scheduler_running': scheduler.running,
                'active_job_count': len(scheduler.get_jobs())
            }
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5555) 