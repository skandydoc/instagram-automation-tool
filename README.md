# Instagram Automation Tool

A comprehensive Python Flask application for automating Instagram posts across multiple business accounts. Features include content scheduling, hashtag management, caption templates, analytics tracking, and support for Feed Posts, Stories, Carousels, and Reels.

## 🚀 Current Features

### ✅ **Fully Implemented & Working**
- **Multi-Account Management**: Manage up to 20 Instagram business accounts
- **Feed Post Automation**: Single image posts with captions and hashtags
- **Carousel Posts**: Multi-image posts (up to 10 images) with drag-and-drop reordering
- **Reel Posts**: Video content posting with proper format validation
- **Smart Scheduling**: Schedule posts with 1 PM and 10 PM IST slots with ±15 minute variance
- **Content Upload**: Easy drag-and-drop image upload interface
- **Caption Templates**: Pre-built templates with variable substitution
- **Hashtag Repository**: Automated hashtag selection from curated collection
- **Google Cloud Storage**: Automatic image hosting for public URLs
- **Real-time Status**: Monitor post status (scheduled, posted, failed)
- **Error Handling**: Comprehensive error reporting and validation
- **Test Account System**: Development mode for testing without real API calls

### 🔄 **Partially Implemented**
- **Story Posts**: API integration complete, UI pending (Page admin validation required)
- **Analytics Dashboard**: Basic tracking implemented, advanced metrics pending
- **Bulk Upload**: Framework ready, UI implementation pending

### 📋 **Planned Features**
- **Story Builder UI**: Text overlays, polls, mentions, links
- **Advanced Analytics**: Engagement tracking, performance metrics
- **Bulk Scheduling**: Multiple posts at once
- **Template Management**: Create and manage custom templates
- **API Rate Limiting**: Smart queuing for daily limits

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- Instagram Business Account(s)
- Facebook Business Manager access
- Instagram Graph API access token
- Google Cloud Storage (optional, for production)

### Setup Steps

1. **Clone and Setup Environment**
   ```bash
   cd instagram
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   Update the `.env` file with your credentials:
   ```bash
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-change-this-in-production
   DATABASE_URL=sqlite:///instagram_automation.db
   INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token_here
   TIMEZONE=Asia/Kolkata

   # Google Cloud Storage Configuration (Optional)
   GCS_BUCKET_NAME=your-bucket-name
   GCS_PROJECT_ID=your-project-id
   ```

3. **Start the Application**
   ```bash
   source venv/bin/activate
   python app.py
   ```

4. **Access the Dashboard**
   Open http://localhost:5555 in your browser

## 📋 Getting Instagram API Credentials

### Step 1: Facebook Business Manager Setup
1. Go to [Facebook Business Manager](https://business.facebook.com)
2. Connect your Instagram Business Account
3. Create a Facebook App with Instagram permissions
4. Add your Instagram account to the app

### Step 2: Get Instagram Account ID
1. In Facebook Business Manager, go to Business Settings
2. Click on Instagram Accounts
3. Find your account and copy the Instagram Account ID (17-18 digit number)

### Step 3: Generate Access Token
1. Go to [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer)
2. Select your app and generate a user access token
3. Convert it to a long-lived token (60 days)
4. Ensure it has these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `pages_show_list`

## 🎯 Usage Guide

### 1. Initialize Database
- Visit http://localhost:5555/init_db to set up initial data
- This creates sample hashtags and caption templates

### 2. Add Instagram Account
1. Go to **Accounts** → **Add New Account**
2. Enter your Instagram username
3. Enter your Instagram Account ID (17-18 digits)
4. Paste your access token
5. Select account niche (optional)
6. Click **Add Account**

### 3. Upload and Schedule Content
1. Go to **Upload Content**
2. Select the target account
3. Drag & drop or select an image file
4. Choose a caption template or write custom text
5. Select scheduling option:
   - **Post Now**: Immediate posting
   - **Next Available Slot**: Schedule for next 1 PM or 10 PM slot
6. Click **Upload and Schedule**

### 4. Monitor Posts
- Visit **Posts & Schedule** to view all scheduled and posted content
- Filter by account, status, or date range
- View post details, captions, and error messages
- Track posting success and failure rates

### 5. Account Management
- View account statistics and posting schedules
- Monitor posting frequency and success rates
- Manage account settings and status

## 📊 Dashboard Features

### Main Dashboard
- **Quick Stats**: Total posts, success rate, pending posts, failed posts
- **Account Overview**: List of connected accounts with status
- **Recent Activity**: Latest posts and their status
- **Quick Actions**: Easy access to main functions

### Analytics
- Post success/failure rates
- Account-specific performance metrics
- Engagement tracking (when available)
- Historical posting data

## ⚙️ Configuration

### Posting Schedule
- **Morning Slot**: 1:00 PM IST (±15 minutes variance)
- **Evening Slot**: 10:00 PM IST (±15 minutes variance)
- **Timezone**: Asia/Kolkata (IST)
- **Rate Limiting**: Respects Instagram's API limits (25 posts/day)

### Content Requirements
- **Image Formats**: JPG, PNG, GIF
- **Video Formats**: MP4 with H.264 codec, AAC audio
- **File Size**: Maximum 100MB per file
- **Carousel**: Up to 10 images per post
- **Public URLs**: Images must be publicly accessible for Instagram API

### Hashtags
- Automatically adds 15-20 hashtags from repository
- Categories: General, Business, Lifestyle, Personal, Daily, Engagement
- Random selection to avoid repetition

## 🔧 API Testing

Test your Instagram API integration:
```bash
curl http://localhost:5555/test_api
```

Expected response:
```json
{
  "status": "success",
  "instagram_api": "available",
  "token_validation": {
    "valid": true,
    "message": "Valid format"
  },
  "base_url": "https://graph.facebook.com/v18.0",
  "message": "Instagram API integration is working"
}
```

## 🚨 Troubleshooting

### Common Issues

1. **"Invalid Instagram account or access token"**
   - Verify your Instagram Account ID is 17-18 digits
   - Check access token format (starts with "EAA")
   - Ensure token has required permissions
   - Confirm account is a Business/Creator account

2. **"Image URL must be a valid HTTP/HTTPS URL"**
   - Instagram requires publicly accessible image URLs
   - For testing: ensure app is running on accessible port
   - For production: use cloud storage (Google Cloud Storage, AWS S3)

3. **Posts failing to publish**
   - Check Instagram API rate limits
   - Verify account permissions
   - Ensure image URLs are accessible
   - Check error messages in post details

4. **Story posts appearing in feed**
   - Ensure Page admin permissions are properly set
   - Verify Facebook Business Manager connection
   - Check Instagram account type (must be Business/Creator)

5. **Database errors**
   - Run `/init_db` to initialize database
   - Check file permissions in project directory
   - Verify SQLite is working properly

## 📝 Development Notes

### Current Technical Stack
- **Backend**: Python Flask with SQLAlchemy
- **Database**: SQLite (production: PostgreSQL recommended)
- **Storage**: Google Cloud Storage for public URLs
- **Scheduling**: APScheduler for background tasks
- **UI**: Bootstrap 5 with vanilla JavaScript
- **API**: Instagram Graph API v18.0

### For Production Deployment
1. **Environment Variables**: Set proper production values
2. **Secret Key**: Generate secure random secret key
3. **Image Storage**: Implement cloud storage (Google Cloud Storage recommended)
4. **Database**: Consider PostgreSQL for better performance
5. **SSL**: Use HTTPS for secure API communications
6. **Rate Limiting**: Implement additional rate limiting if needed

### File Structure
```
instagram/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables
├── templates/            # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── accounts.html
│   ├── add_account.html
│   ├── upload.html
│   └── posts.html
├── uploads/              # Temporary file storage
├── story_post.py         # Story posting script
├── carousel_post.py      # Carousel posting script
├── test_post_reel.py     # Reel posting script
└── instagram_automation.db # SQLite database
```

## 🔒 Security Considerations

- Keep access tokens secure and private
- Regularly rotate access tokens
- Use environment variables for sensitive data
- Implement proper authentication for production use
- Monitor API usage to stay within limits
- Regular backups of database and content

## 📞 Support

For issues related to:
- **Instagram API**: Check [Instagram Graph API Documentation](https://developers.facebook.com/docs/instagram-api)
- **Facebook Business Manager**: Visit [Facebook Business Help Center](https://www.facebook.com/business/help)
- **Application Bugs**: Check error logs and console output

## 🎉 Getting Started Checklist

- [ ] Python environment set up
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Instagram Business account connected to Facebook
- [ ] Access token generated with proper permissions
- [ ] Database initialized (`/init_db`)
- [ ] First account added successfully
- [ ] Test post uploaded and scheduled
- [ ] Dashboard showing correct statistics

## 🚀 Recent Updates

### v1.2.0 (Current)
- ✅ Fixed JavaScript template issues in accounts.html
- ✅ Enhanced Google Cloud Storage integration
- ✅ Improved error handling and validation
- ✅ Added comprehensive API testing endpoints
- ✅ Implemented carousel posting (up to 10 images)
- ✅ Added reel posting with video format validation
- ✅ Enhanced file upload with drag-and-drop
- ✅ Improved UI responsiveness and user experience

### v1.1.0
- ✅ Multi-account Instagram management
- ✅ Smart scheduling with time variance
- ✅ Caption templates with variable substitution
- ✅ Hashtag repository system
- ✅ Real-time post status tracking

### v1.0.0
- ✅ Basic Flask application setup
- ✅ Instagram Graph API integration
- ✅ SQLite database with SQLAlchemy
- ✅ Bootstrap UI framework

---

**Ready to automate your Instagram presence!** 🚀

Start by visiting http://localhost:5555 and following the setup steps above. 