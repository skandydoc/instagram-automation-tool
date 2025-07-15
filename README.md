# Instagram Automation Tool

A comprehensive Instagram automation tool that supports **Feed Posts**, **Stories**, and **Carousels** with intelligent scheduling and account management.

## 🚀 Features

### ✅ Post Types Supported
- **Feed Posts**: Traditional Instagram posts with captions and hashtags
- **Stories**: Photo stories with text overlays, polls (up to 4 options), mentions, and links
- **Carousels**: Multi-image posts (up to 20 images) with smart ordering

### ✅ Key Capabilities
- **Multi-Account Management**: Manage multiple Instagram business accounts
- **Smart Scheduling**: Automatic scheduling with daily limits (25 posts per account)
- **Template System**: Pre-built caption and story templates
- **File Management**: Account-specific folders with cloud storage support
- **Real-time Preview**: Live preview of posts, stories, and carousels
- **API Access**: Complete REST API for programmatic posting
- **Analytics Ready**: Built-in metrics tracking for all post types

### ✅ Advanced Features
- **Story Auto-Scheduling**: Stories posted every 2 hours (6 AM - 2 AM)
- **Daily Limits**: Automatic queuing when daily limits are reached
- **Cloud Storage**: Google Cloud Storage integration with fallback options
- **Test Mode**: Development-friendly test accounts
- **Responsive UI**: Modern Bootstrap-based interface

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **Frontend**: Bootstrap 5 + JavaScript
- **Storage**: Google Cloud Storage
- **Scheduling**: APScheduler
- **API**: Instagram Graph API

## 📋 Prerequisites

1. **Instagram Business Account** connected to Facebook Business Manager
2. **Facebook App** with Instagram permissions
3. **Python 3.8+**
4. **Google Cloud Account** (optional, for production file hosting)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/skandydoc/instagram-automation-tool.git
cd instagram-automation-tool
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instagram_automation.db
GCS_BUCKET_NAME=your-bucket-name
GCS_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### 4. Initialize Database
```bash
python app.py
# Visit http://localhost:5001/init_db to initialize
```

### 5. Add Test Account (Development)
- Username: `test_demo`
- Instagram ID: `test123456`
- Access Token: `test_token_12345`

### 6. Run Application
```bash
python app.py
```
Visit: http://localhost:5001

## 📖 Usage Guide

### Adding Real Instagram Accounts

1. **Get Instagram Account ID**:
   - Go to Facebook Business Manager → Business Settings → Instagram Accounts
   - Copy the 17-18 digit Account ID

2. **Generate Access Token**:
   - Use Facebook Graph API Explorer
   - Required permissions: `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`, `pages_show_list`
   - Convert to long-lived token (60 days)

3. **Add Account**: Go to `/add_account` and fill in the details

### Creating Content

#### Feed Posts
- Upload single image
- Add caption (with templates)
- Schedule: Now, Next Slot, or Specific Time
- Automatic hashtag addition

#### Stories
- Upload story image (9:16 ratio recommended)
- Add text overlays, polls (up to 4 options), mentions, links
- Auto-scheduling: Every 2 hours during day
- Real-time preview in story frame

#### Carousels
- Upload multiple images (2-20)
- Drag-and-drop reordering
- Unified caption for all images
- Smart filename-based ordering

## 🔌 API Documentation

### Base URL: `http://localhost:5001/api`

#### Get Accounts
```bash
GET /api/accounts
```

#### Create Post
```bash
POST /api/post
Content-Type: multipart/form-data

# Feed Post
account_id=1&post_type=feed&file=@image.jpg&caption=Hello World

# Story
account_id=1&post_type=story&file=@story.jpg&overlay_text=Story Text

# Carousel
account_id=1&post_type=carousel&files[]=@img1.jpg&files[]=@img2.jpg&caption=Carousel
```

#### Check Status
```bash
GET /api/status/{post_id}
```

See `API_DOCUMENTATION.md` for complete API reference.

## 📁 Project Structure

```
instagram-automation-tool/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── dashboard.html    # Main dashboard
│   ├── upload.html       # Upload interface (tabbed)
│   ├── accounts.html     # Account management
│   └── posts.html        # Scheduled posts view
├── uploads/              # File storage
│   └── {account_id}/     # Account-specific folders
│       ├── feed/         # Feed post images
│       ├── stories/      # Story images
│       └── carousels/    # Carousel images
├── instance/             # Database storage
└── README.md
```

## 🎯 Database Schema

### Key Tables
- **Account**: Instagram account management
- **Post**: All post types with flexible schema
- **CaptionTemplate**: Reusable caption templates
- **StoryTemplate**: Story text overlay templates
- **PostMetrics**: Analytics tracking
- **PostingSchedule**: Account-specific scheduling

## 🔧 Configuration

### Daily Limits
- **Total Posts**: 25 per account per day (all types combined)
- **Stories**: 10 per day (auto-scheduled every 2 hours)
- **Feed Posts**: Scheduled at 1 PM and 10 PM IST (±15 min variance)

### File Storage
- **Development**: Local filesystem with localhost URLs
- **Production**: Google Cloud Storage with public URLs
- **Fallback**: ngrok tunneling support

## 🚀 Deployment

### Google Cloud Run (Recommended)
1. Set up Google Cloud Storage bucket
2. Configure service account with storage permissions
3. Deploy using `gcloud run deploy`
4. Set environment variables

### Local Development
- Uses SQLite database
- Files served from localhost
- Test accounts for safe development

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check `API_DOCUMENTATION.md` and `UpdatedPRD.md`
- **Issues**: Submit GitHub issues for bugs and feature requests
- **Setup Help**: Visit `/setup_help` in the application

## 🎯 Roadmap

- [ ] Video support for Stories and Posts
- [ ] Advanced analytics dashboard
- [ ] Multi-language caption templates
- [ ] Instagram Reels support
- [ ] Bulk upload interface
- [ ] Advanced scheduling (time zones, holidays)
- [ ] User authentication system
- [ ] Team collaboration features

---

**Repository**: https://github.com/skandydoc/instagram-automation-tool

**Live Demo**: *Coming Soon*

Made with ❤️ for Instagram automation 