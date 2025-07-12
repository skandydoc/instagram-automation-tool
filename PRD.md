# Instagram Automation Tool - Product Requirements Document

## 1. Project Overview

### 1.1 Project Name
Instagram Multi-Account Automation Platform

### 1.2 Project Description
A Flask-based web application for automating Instagram posts, stories, and content scheduling across multiple business accounts. The platform will manage up to 20 Instagram business accounts, schedule posts up to 1 month in advance, and provide comprehensive analytics for engagement optimization.

### 1.3 Business Objectives
- Automate content posting across 20 Instagram business accounts
- Maximize reach and engagement through strategic scheduling and hashtag optimization
- Provide centralized management for multi-account Instagram marketing
- Ensure compliance with Instagram's API policies and rate limits

### 1.4 Success Metrics
- Successfully schedule and post 1,200+ posts per month (20 accounts × 2 posts/day × 30 days)
- Achieve 95%+ post success rate (posts published without errors)
- Reduce manual posting time by 90%
- Increase average engagement rate by 25% through optimized scheduling

## 2. Technical Architecture

### 2.1 Technology Stack
- **Backend**: Python Flask 2.x
- **Database**: SQLite 3.x
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5
- **APIs**: Instagram Graph API, Google Drive API
- **Cloud Platform**: Google Cloud Run
- **Storage**: Google Drive (backup), Local file system (temporary)
- **Deployment**: GitHub Actions CI/CD

### 2.2 System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │────│   Flask App     │────│   SQLite DB     │
│   (Dashboard)   │    │  (Cloud Run)    │    │   (Persistent)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ├─────────────────┐
                              │                 │
                    ┌─────────────────┐ ┌─────────────────┐
                    │Instagram Graph  │ │ Google Drive    │
                    │     API         │ │     API         │
                    └─────────────────┘ └─────────────────┘
```

### 2.3 Database Schema

#### 2.3.1 Tables Structure

**accounts**
```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    instagram_id VARCHAR(255) UNIQUE NOT NULL,
    access_token TEXT NOT NULL,
    account_type VARCHAR(50) DEFAULT 'business',
    niche VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**posts**
```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    content_type VARCHAR(50) NOT NULL, -- 'image', 'carousel', 'story'
    caption TEXT,
    media_urls TEXT, -- JSON array of image URLs
    hashtags TEXT, -- JSON array of hashtags
    scheduled_time TIMESTAMP NOT NULL,
    actual_post_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'scheduled', -- 'scheduled', 'posted', 'failed', 'cancelled'
    instagram_post_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

**post_analytics**
```sql
CREATE TABLE post_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    saves_count INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);
```

**hashtag_repository**
```sql
CREATE TABLE hashtag_repository (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hashtag VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(100),
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**caption_templates**
```sql
CREATE TABLE caption_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    template TEXT NOT NULL,
    variables TEXT, -- JSON array of variable names
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**story_templates**
```sql
CREATE TABLE story_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    text_overlay TEXT NOT NULL,
    font_size INTEGER DEFAULT 24,
    font_color VARCHAR(7) DEFAULT '#FFFFFF',
    background_color VARCHAR(7) DEFAULT '#000000',
    position_x INTEGER DEFAULT 50, -- percentage from left
    position_y INTEGER DEFAULT 50, -- percentage from top
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**system_settings**
```sql
CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**posting_schedule**
```sql
CREATE TABLE posting_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    time_slot_1 TIME NOT NULL, -- Morning post time
    time_slot_2 TIME NOT NULL, -- Evening post time
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    variance_minutes INTEGER DEFAULT 15,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

## 3. Feature Specifications

### 3.1 Account Management

#### 3.1.1 Account Registration
- **Input**: Instagram username, access token, niche category
- **Process**: Validate token, fetch account details via Graph API
- **Output**: Account added to database with active status
- **Validation**: Verify business account type, valid permissions

#### 3.1.2 Account Dashboard
- **Display**: List of all connected accounts
- **Information**: Username, follower count, post count, status, last post time
- **Actions**: View details, edit settings, deactivate/activate
- **Refresh**: Auto-refresh account metrics every 30 minutes

### 3.2 Content Management

#### 3.2.1 Content Upload Interface
- **File Types**: JPEG, PNG, MP4 (for stories)
- **Upload Limit**: 10 files per carousel, 100MB per file
- **Validation**: Image dimensions, file size, format compatibility
- **Storage**: Temporary local storage, backup to Google Drive
- **Processing**: Auto-generate thumbnails, extract metadata

#### 3.2.2 Bulk Upload Workflow
```
1. User selects multiple images (up to 50 per session)
2. System validates each file
3. User assigns content to accounts and date ranges
4. System generates scheduling grid
5. User reviews and confirms schedule
6. System creates post records in database
```

#### 3.2.3 Google Drive Integration
- **Purpose**: Backup storage for uploaded content
- **Structure**: 
  ```
  /Instagram_Automation/
    ├── /account_1/
    │   ├── /posts/
    │   └── /stories/
    ├── /account_2/
    │   ├── /posts/
    │   └── /stories/
    └── /templates/
  ```
- **Sync**: Auto-upload after successful local processing
- **Cleanup**: Remove local files after 24 hours

### 3.3 Scheduling System

#### 3.3.1 Posting Schedule Configuration
- **Default Times**: 1:00 PM and 10:00 PM IST
- **Variance**: ±15 minutes random variation
- **Customization**: Account-specific time slots
- **Timezone**: Asia/Kolkata (IST) for all accounts
- **Weekend Handling**: Same schedule as weekdays

#### 3.3.2 Intelligent Scheduling Algorithm
```python
def calculate_post_time(base_time, variance_minutes):
    """
    Calculate actual posting time with random variance
    """
    variance_seconds = variance_minutes * 60
    random_offset = random.randint(-variance_seconds, variance_seconds)
    return base_time + timedelta(seconds=random_offset)
```

#### 3.3.3 Rate Limiting & Compliance
- **Rate Limits**: Maximum 25 posts per account per day (Instagram limit)
- **Spacing**: Minimum 5 minutes between posts per account
- **Global Spacing**: Minimum 30 seconds between any posts across all accounts
- **Retry Logic**: 3 attempts with exponential backoff (1min, 5min, 15min)
- **Failure Handling**: Mark as failed, notify admin, log error details

### 3.4 Caption & Hashtag Management

#### 3.4.1 Caption Templates
- **Variables**: `{account_name}`, `{date}`, `{time}`, `{day_of_week}`, `{custom_text}`
- **Categories**: Motivational, Product, Engagement, Seasonal
- **Example Template**: 
  ```
  "Good {time_period} from {account_name}! 🌟
  
  {custom_text}
  
  What's your favorite part about {day_of_week}? Tell us in the comments! 👇
  
  #MotivationMonday #Inspiration #GoodVibes"
  ```

#### 3.4.2 Hashtag Management
- **Common Repository**: 50-100 general hashtags
- **Categories**: General, Trending, Niche-specific, Location-based
- **Rotation Logic**: Randomly select 15-20 hashtags per post
- **Trending Integration**: Manual update of trending hashtags weekly
- **Hashtag Limits**: Maximum 30 hashtags per post (Instagram limit)

### 3.5 Story Automation

#### 3.5.1 Story Creation
- **Input**: Base image + text overlay template
- **Text Positioning**: Predefined positions (top, center, bottom)
- **Styling**: Font size (16-48px), color (white/black), background overlay
- **Duration**: 24-hour story lifespan (Instagram default)
- **Frequency**: 1 story per account per day (optional)

#### 3.5.2 Story Templates
- **Template 1**: "Good Morning!" with motivational quote
- **Template 2**: "Behind the Scenes" with custom text
- **Template 3**: "Tip of the Day" with educational content
- **Template 4**: "Thank You" with engagement message

### 3.6 Analytics & Reporting

#### 3.6.1 Performance Metrics
- **Engagement Rate**: (Likes + Comments + Shares) / Reach × 100
- **Growth Metrics**: Follower growth, post reach, impressions
- **Content Performance**: Best performing posts, optimal posting times
- **Account Comparison**: Cross-account performance analysis

#### 3.6.2 Analytics Dashboard
- **Time Ranges**: Last 7 days, 30 days, 90 days, custom range
- **Visualizations**: Line charts, bar charts, heatmaps
- **Export**: CSV/PDF reports
- **Alerts**: Performance drops, unusual patterns

#### 3.6.3 Data Collection Schedule
- **Real-time**: Post success/failure status
- **Hourly**: Recent post engagement (first 6 hours)
- **Daily**: Full analytics refresh for all posts
- **Weekly**: Trend analysis and reporting

## 4. User Interface Specifications

### 4.1 Dashboard Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Header: Logo | Navigation | Account Selector | User Profile     │
├─────────────────────────────────────────────────────────────────┤
│ Sidebar: Dashboard | Accounts | Content | Schedule | Analytics  │
├─────────────────────────────────────────────────────────────────┤
│ Main Content Area:                                              │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│ │ Quick Stats     │ │ Recent Posts    │ │ Today's Queue   │   │
│ │ - Total Posts   │ │ - Success Rate  │ │ - Pending: 5    │   │
│ │ - Engagement    │ │ - Failed: 2     │ │ - Posted: 15    │   │
│ │ - Reach         │ │ - Avg Response  │ │ - Failed: 1     │   │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Calendar View
- **Layout**: Monthly calendar grid
- **Post Indicators**: Color-coded dots for each account
- **Hover Details**: Post preview, scheduled time, account
- **Drag & Drop**: Reschedule posts by dragging
- **Filters**: By account, date range, status
- **Zoom**: Day, week, month views

### 4.3 Content Upload Interface
- **Drag & Drop Zone**: Large central area for file uploads
- **File Preview**: Thumbnail grid with filename, size, status
- **Batch Actions**: Select all, remove selected, clear all
- **Upload Progress**: Progress bar with success/error indicators
- **Validation Messages**: Real-time file validation feedback

### 4.4 Scheduling Interface
- **Account Selection**: Multi-select dropdown with account thumbnails
- **Date Range Picker**: Start date, end date, specific dates
- **Time Slots**: Morning/evening time configuration
- **Caption Assignment**: Template selection + custom text
- **Hashtag Selection**: Checkboxes for hashtag categories
- **Preview**: Final post preview before scheduling

### 4.5 Mobile Responsiveness
- **Breakpoints**: 
  - Mobile: 320px - 768px
  - Tablet: 768px - 1024px
  - Desktop: 1024px+
- **Navigation**: Collapsible sidebar on mobile
- **Touch Optimized**: Larger touch targets, swipe gestures
- **Progressive Web App**: Offline capability for viewing scheduled posts

## 5. API Integrations

### 5.1 Instagram Graph API Integration

#### 5.1.1 Authentication Flow
```python
# Initial setup with long-lived token
INSTAGRAM_ACCESS_TOKEN = "EAAPLeLizF4oBPKv8wFz2bp4Tbtd9voimZCQRNmUIubw1UemVNHFdZAy3UZAw6nTXH2CR2EcZCXeKW6tDSYZBoeDjfclA9oyEpWAl7jzvzdnP2L3NB7iatx0D9AuZAZBwBrwZC7MI7fPzGMMPlzOfrZC1p9kAwBRZAQjc4nXgUakuJlodWIPMMHlAZAyWTaeWtrJzqIu"

# Required permissions for Business Manager app
REQUIRED_PERMISSIONS = [
    'instagram_basic',
    'instagram_content_publish',
    'pages_read_engagement',
    'pages_show_list'
]
```

#### 5.1.2 API Endpoints Usage
- **Account Info**: `GET /{instagram-account-id}?fields=account_type,username,followers_count,media_count`
- **Media Upload**: `POST /{instagram-account-id}/media` (container creation)
- **Media Publish**: `POST /{instagram-account-id}/media_publish`
- **Story Upload**: `POST /{instagram-account-id}/media` (story container)
- **Analytics**: `GET /{media-id}/insights?metric=impressions,reach,engagement`

#### 5.1.3 Error Handling
- **Rate Limiting**: Implement exponential backoff
- **Token Expiry**: Graceful handling with admin notification
- **API Errors**: Log detailed error responses
- **Network Issues**: Retry logic with circuit breaker pattern

### 5.2 Google Drive API Integration

#### 5.2.1 Setup Requirements
- **Service Account**: Create service account with Drive API access
- **Credentials**: Download JSON credentials file
- **Folder Structure**: Create organized folder hierarchy
- **Permissions**: Grant service account write access to backup folder

#### 5.2.2 Integration Functions
```python
def upload_to_drive(file_path, account_folder, content_type):
    """Upload file to Google Drive backup"""
    
def create_folder_structure(account_id):
    """Create account-specific folder structure"""
    
def cleanup_old_files(days_old=30):
    """Remove old backup files to manage storage"""
```

## 6. Security & Compliance

### 6.1 Instagram API Compliance
- **Rate Limiting**: Respect all Instagram API rate limits
- **Content Policies**: Ensure all content meets Instagram guidelines
- **Automation Detection**: Implement human-like posting patterns
- **Terms of Service**: Full compliance with Instagram Business API terms

### 6.2 Data Security
- **Token Storage**: Encrypt access tokens in database
- **File Security**: Temporary file cleanup after processing
- **Database Security**: SQLite file permissions and backup encryption
- **API Keys**: Environment variable storage for sensitive data

### 6.3 Privacy Compliance
- **Data Retention**: Automatic cleanup of old analytics data
- **User Data**: Minimal collection, secure storage
- **Audit Logging**: Track all system actions and API calls
- **Backup Security**: Encrypted backups with access controls

## 7. Deployment & Infrastructure

### 7.1 Google Cloud Run Configuration
```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/instagram-automation', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/instagram-automation']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', 'instagram-automation',
      '--image', 'gcr.io/$PROJECT_ID/instagram-automation',
      '--region', 'asia-south2',
      '--platform', 'managed',
      '--allow-unauthenticated'
    ]
```

### 7.2 Environment Configuration
```bash
# Production environment variables
FLASK_ENV=production
INSTAGRAM_ACCESS_TOKEN=<encrypted_token>
GOOGLE_DRIVE_CREDENTIALS=<path_to_credentials>
DATABASE_URL=sqlite:///instagram_automation.db
SECRET_KEY=<random_secret_key>
TIMEZONE=Asia/Kolkata
```

### 7.3 Monitoring & Logging
- **Application Logs**: Structured logging with timestamps
- **Error Tracking**: Exception logging with stack traces
- **Performance Monitoring**: Request/response times
- **Business Metrics**: Posts scheduled, posted, failed
- **Alerting**: Email notifications for critical errors

### 7.4 Backup Strategy
- **Database Backup**: Daily automated SQLite backup to Google Drive
- **Code Backup**: Git repository with version control
- **Configuration Backup**: Environment variables and settings
- **Recovery Plan**: Documented recovery procedures

## 8. Testing Strategy

### 8.1 Unit Testing
- **Database Operations**: Test all CRUD operations
- **API Integrations**: Mock API responses for testing
- **Scheduling Logic**: Test time calculations and variance
- **File Processing**: Test upload, validation, and processing

### 8.2 Integration Testing
- **End-to-End Workflows**: Complete posting workflow
- **API Integration**: Real API calls with test accounts
- **Database Integration**: Full database operations
- **User Interface**: Selenium-based UI testing

### 8.3 Performance Testing
- **Load Testing**: Simulate 20 accounts with high post volume
- **Stress Testing**: Test system limits and error handling
- **API Rate Limiting**: Test rate limit handling
- **Database Performance**: Test with large datasets

## 9. Maintenance & Support

### 9.1 Regular Maintenance Tasks
- **Database Optimization**: Monthly database cleanup and optimization
- **Log Rotation**: Weekly log cleanup and archiving
- **Security Updates**: Monthly dependency updates
- **Performance Monitoring**: Weekly performance review

### 9.2 Support Procedures
- **Issue Tracking**: Structured issue reporting and tracking
- **Documentation**: Comprehensive user and admin documentation
- **Training Materials**: Video tutorials and user guides
- **Escalation Process**: Clear escalation path for critical issues

## 10. Future Enhancements

### 10.1 Phase 2 Features
- **Advanced Analytics**: AI-powered insights and recommendations
- **Content Generation**: AI-assisted caption and hashtag generation
- **Multi-platform**: Extension to Facebook, Twitter, LinkedIn
- **Team Collaboration**: Multi-user access with role-based permissions

### 10.2 Scalability Improvements
- **Database Migration**: Move to PostgreSQL for better performance
- **Microservices**: Split into separate services for posting, analytics, etc.
- **Caching**: Redis integration for improved performance
- **CDN Integration**: Content delivery network for faster image loading

## 11. Success Criteria

### 11.1 Technical Success Metrics
- **Uptime**: 99.9% application availability
- **Performance**: < 2 second page load times
- **Reliability**: 95% post success rate
- **Scalability**: Handle 20 accounts with 60 posts/day

### 11.2 Business Success Metrics
- **User Adoption**: 100% of target accounts connected
- **Engagement Growth**: 25% increase in average engagement rate
- **Time Savings**: 90% reduction in manual posting time
- **ROI**: Positive return on investment within 3 months

### 11.3 User Experience Metrics
- **User Satisfaction**: 4.5/5 user rating
- **Feature Adoption**: 80% of features actively used
- **Support Tickets**: < 5 support tickets per month
- **Learning Curve**: New users productive within 30 minutes

---

## Appendix A: Technical Implementation Timeline

### Week 1-2: Foundation Setup
- Project structure and environment setup
- Database schema implementation
- Basic Flask application with routing
- Instagram API integration setup

### Week 3-4: Core Features
- Account management system
- Content upload and processing
- Basic scheduling functionality
- Database operations and models

### Week 5-6: Advanced Features
- Calendar view implementation
- Bulk upload functionality
- Analytics dashboard
- Story automation features

### Week 7-8: Integration & Testing
- Google Drive API integration
- Comprehensive testing
- Performance optimization
- Security hardening

### Week 9-10: Deployment & Polish
- Google Cloud Run deployment
- CI/CD pipeline setup
- User interface polish
- Documentation completion

## Appendix B: API Rate Limits Reference

### Instagram Graph API Limits
- **Posts**: 25 posts per account per day
- **API Calls**: 200 calls per hour per app
- **Media Upload**: 1000 media uploads per day per app
- **Analytics**: 5000 insights API calls per day

### Google Drive API Limits
- **Queries**: 1000 queries per 100 seconds per user
- **Uploads**: 750 uploads per 100 seconds per user
- **Storage**: 15GB free storage per account

## Appendix C: Database Indexes

```sql
-- Performance optimization indexes
CREATE INDEX idx_posts_account_scheduled ON posts(account_id, scheduled_time);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_analytics_post_updated ON post_analytics(post_id, last_updated);
CREATE INDEX idx_accounts_active ON accounts(is_active);
CREATE INDEX idx_hashtags_category ON hashtag_repository(category, is_active);
```

This PRD serves as the complete specification for the Instagram Automation Tool implementation. 