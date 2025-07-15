# Instagram Automation Tool - API Documentation

This document provides comprehensive API documentation for the Instagram Automation Tool, including the new Stories and Carousel functionality.

## Overview

The Instagram Automation Tool now supports three types of content:
- **Feed Posts**: Traditional Instagram posts with single images
- **Stories**: Instagram stories with interactive elements (text overlays, polls, mentions, links)
- **Carousels**: Multi-image posts (up to 20 images)

## Base URL

```
http://localhost:5555
```

## Authentication

Currently, no authentication is required for API endpoints. In production, implement proper API key authentication.

## Content Types

The API supports both JSON and multipart/form-data for file uploads.

---

## 📱 Post Creation API

### Create Post (Unified Endpoint)

**Endpoint:** `POST /api/post`  
**Description:** Create a new post (Feed, Story, or Carousel)

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `account_id` | integer | Yes | ID of the Instagram account |
| `post_type` | string | No | Type of post: `feed`, `story`, `carousel` (default: `feed`) |
| `schedule_type` | string | No | When to post: `now`, `next_slot`, `specific`, `queue` (default: `now`) |
| `include_hashtags` | boolean | No | Whether to include automatic hashtags (default: `true`) |

#### Feed Post Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `caption` | string | Yes* | Post caption text |
| `caption_template` | string | Yes* | Template ID or text with variables |
| `file` | file | Yes | Image file to upload |

*Either `caption` or `caption_template` is required.

#### Story Post Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | Yes | Story image file |
| `text_overlay` | string | No | Text to overlay on story |
| `text_position` | string | No | Position: `top`, `center`, `bottom` |
| `text_style` | string | No | Style: `default`, `bold`, `elegant` |
| `poll_question` | string | No | Poll question text |
| `poll_option_1` | string | No | First poll option |
| `poll_option_2` | string | No | Second poll option |
| `poll_option_3` | string | No | Third poll option (optional) |
| `poll_option_4` | string | No | Fourth poll option (optional) |
| `mentions` | string/array | No | Comma-separated usernames or array |
| `link_url` | string | No | URL for swipe up link |
| `link_text` | string | No | Link text (default: "Swipe up") |

#### Carousel Post Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `caption` | string | Yes* | Carousel caption |
| `caption_template` | string | Yes* | Template with variables |
| `file1`, `file2`, ... `file20` | file | Yes | Image files (max 20) |

*Either `caption` or `caption_template` is required.

#### Example Requests

**Feed Post (Form Data):**
```bash
curl -X POST http://localhost:5555/api/post \
  -F "account_id=1" \
  -F "post_type=feed" \
  -F "caption=Check out this amazing view! 🌅" \
  -F "schedule_type=now" \
  -F "file=@image.jpg"
```

**Story with Poll (Form Data):**
```bash
curl -X POST http://localhost:5555/api/post \
  -F "account_id=1" \
  -F "post_type=story" \
  -F "text_overlay=What do you think?" \
  -F "text_position=top" \
  -F "poll_question=How was your day?" \
  -F "poll_option_1=😊 Great" \
  -F "poll_option_2=😐 Okay" \
  -F "poll_option_3=😞 Not great" \
  -F "file=@story_image.jpg"
```

**Carousel (Form Data):**
```bash
curl -X POST http://localhost:5555/api/post \
  -F "account_id=1" \
  -F "post_type=carousel" \
  -F "caption=Swipe to see all the highlights! ➡️" \
  -F "file1=@image1.jpg" \
  -F "file2=@image2.jpg" \
  -F "file3=@image3.jpg"
```

#### Response Format

**Success (201 Created):**
```json
{
  "success": true,
  "message": "Feed post created successfully",
  "post_id": 123,
  "scheduled_time": "2024-07-15T10:30:00.000000"
}
```

**Error (400 Bad Request):**
```json
{
  "error": "caption or caption_template is required"
}
```

---

## 📊 Status & Information APIs

### Get Post Status

**Endpoint:** `GET /api/status/{post_id}`  
**Description:** Get the current status of a specific post

#### Response Format

```json
{
  "id": 123,
  "post_type": "feed",
  "status": "posted",
  "scheduled_time": "2024-07-15T10:30:00.000000",
  "actual_post_time": "2024-07-15T10:30:15.000000",
  "instagram_post_id": "ABC123456789",
  "error_message": null,
  "account_username": "test_account"
}
```

#### Status Values

- `scheduled`: Post is scheduled for future
- `posted`: Successfully posted to Instagram
- `failed`: Post failed with error
- `cancelled`: Post was cancelled

### List Accounts

**Endpoint:** `GET /api/accounts`  
**Description:** Get all active Instagram accounts

#### Response Format

```json
[
  {
    "id": 1,
    "username": "my_business_account",
    "instagram_id": "17841400123456789",
    "account_type": "business",
    "niche": "Travel & Lifestyle",
    "is_active": true
  }
]
```

### List Caption Templates

**Endpoint:** `GET /api/templates`  
**Description:** Get all available caption templates

#### Response Format

```json
[
  {
    "id": 1,
    "name": "Motivational Monday",
    "template": "Good {time_period} from {account_name}! 🌟\n\n{custom_text}\n\nWhat's your motivation for this {day_of_week}?",
    "category": "Motivational",
    "variables": ["custom_text", "account_name", "day_of_week", "time_period"]
  }
]
```

### List Story Templates

**Endpoint:** `GET /api/story-templates`  
**Description:** Get all available story templates

#### Response Format

```json
[
  {
    "id": 1,
    "template_name": "Bold Center Text",
    "template_type": "text_overlay",
    "template_data": {
      "position": "center",
      "font_size": "large",
      "font_weight": "bold",
      "color": "white",
      "background": "semi-transparent"
    }
  },
  {
    "id": 3,
    "template_name": "Like/Dislike Poll",
    "template_type": "poll",
    "template_data": {
      "question": "What do you think?",
      "options": ["👍 Love it", "👎 Not for me", "🤔 Maybe", "💬 Tell me more"]
    }
  }
]
```

---

## 🕐 Scheduling Options

### Schedule Types

| Type | Description | Behavior |
|------|-------------|----------|
| `now` | Post immediately | Executes within seconds |
| `next_slot` | Next available time slot | Uses account's schedule (1 PM or 10 PM IST) |
| `specific` | Specific date/time | Requires `scheduled_time` parameter |
| `queue` | Add to queue | Schedules based on daily limits |
| `auto_story` | Auto-schedule stories | Stories every 2 hours (6 AM - 2 AM) |

### Daily Limits

- **Maximum 25 posts per day per account** (across all post types)
- **Stories**: Auto-scheduled every 2 hours from 6 AM to 2 AM (10 stories/day max)
- **Feed & Carousel**: 1 PM and 10 PM IST with ±15 minute variance

### Story Auto-Scheduling

Stories use a specialized scheduling system:

**Time Slots:** 6 AM, 8 AM, 10 AM, 12 PM, 2 PM, 4 PM, 6 PM, 8 PM, 10 PM, 12 AM, 2 AM

```bash
# Example: Auto-schedule story
curl -X POST http://localhost:5555/api/post \
  -F "account_id=1" \
  -F "post_type=story" \
  -F "schedule_type=auto_story" \
  -F "text_overlay=Daily motivation!" \
  -F "file=@motivation.jpg"
```

---

## 🎨 Story Interactive Elements

### Text Overlays

Position your text overlays with precision:

```json
{
  "text_overlay": "Your text here",
  "text_position": "center",  // top, center, bottom
  "text_style": "bold"        // default, bold, elegant
}
```

### Polls

Create engaging 4-option polls:

```json
{
  "poll_question": "How was your day?",
  "poll_option_1": "😊 Amazing",
  "poll_option_2": "😐 Good", 
  "poll_option_3": "😞 Okay",
  "poll_option_4": "😴 Tired"
}
```

### Mentions

Tag multiple users in your stories:

```bash
# As comma-separated string
-F "mentions=@friend1,@colleague,@brand_partner"

# Or as JSON array
-F "mentions=[\"@friend1\", \"@colleague\", \"@brand_partner\"]"
```

### Links

Add swipe-up links (requires eligible account):

```json
{
  "link_url": "https://example.com",
  "link_text": "Learn More"
}
```

---

## 🖼️ File Management

### Account-Specific Folders

Files are automatically organized by account and post type:

```
uploads/
├── 1/                 # Account ID 1
│   ├── feed/          # Feed post images
│   ├── stories/       # Story images  
│   └── carousels/     # Carousel images
└── 2/                 # Account ID 2
    ├── feed/
    ├── stories/
    └── carousels/
```

### Carousel Image Ordering

Images are automatically ordered by:
1. **Filename numbers**: `image1.jpg`, `image2.jpg`, etc.
2. **Upload order**: If no numbers in filename
3. **Alphabetical**: Fallback ordering

### File Constraints

- **Maximum file size**: 100MB per image
- **Supported formats**: JPEG, PNG
- **Carousel limit**: 20 images maximum
- **Story aspect ratio**: 9:16 recommended

---

## 🔧 Template Variables

### Caption Template Variables

Use these variables in your caption templates:

| Variable | Example Output | Description |
|----------|----------------|-------------|
| `{account_name}` | @my_business | Account username |
| `{custom_text}` | User provided text | Custom text input |
| `{day_of_week}` | Monday | Current day |
| `{date}` | July 15, 2024 | Current date |
| `{time}` | 2:30 PM | Current time |
| `{time_period}` | afternoon | morning/afternoon/evening/night |

### Example Template Usage

```bash
curl -X POST http://localhost:5555/api/post \
  -F "account_id=1" \
  -F "caption_template=Good {time_period} from {account_name}! Today is {day_of_week} and we're sharing: {custom_text}" \
  -F "custom_text=our latest product launch" \
  -F "file=@product.jpg"
```

**Generated Caption:**
```
Good afternoon from @my_business! Today is Monday and we're sharing: our latest product launch

#motivation #business #monday #success #growth
```

---

## ⚠️ Error Handling

### Common Error Responses

**File Too Large:**
```json
{
  "error": "File product.jpg is too large. Maximum size is 100MB."
}
```

**Daily Limit Reached:**
```json
{
  "error": "Daily post limit reached (25 posts). Posts will be queued for tomorrow.",
  "scheduled_time": "2024-07-16T06:00:00.000000"
}
```

**Invalid Post Type:**
```json
{
  "error": "Invalid post_type. Must be: feed, story, or carousel"
}
```

**Missing Required Files:**
```json
{
  "error": "No images were uploaded for the carousel"
}
```

---

## 📈 Production Considerations

### Performance Optimization

1. **Image Optimization**: Compress images before upload
2. **Batch Processing**: Group multiple posts for efficiency
3. **Caching**: Cache templates and account data
4. **Rate Limiting**: Respect Instagram API limits

### Security Recommendations

1. **API Authentication**: Implement API key or JWT authentication
2. **Input Validation**: Sanitize all user inputs
3. **File Validation**: Verify file types and scan for malware
4. **Rate Limiting**: Prevent API abuse

### Monitoring & Analytics

1. **Post Success Rates**: Track successful vs failed posts
2. **Engagement Metrics**: Monitor likes, comments, views
3. **Error Tracking**: Log and alert on failures
4. **Performance Metrics**: API response times and throughput

---

## 🚀 Getting Started

### Quick Start Example

1. **Get available accounts:**
```bash
curl http://localhost:5555/api/accounts
```

2. **Create a simple feed post:**
```bash
curl -X POST http://localhost:5555/api/post \
  -F "account_id=1" \
  -F "caption=Hello World! 🌍" \
  -F "file=@hello.jpg"
```

3. **Check post status:**
```bash
curl http://localhost:5555/api/status/1
```

### Integration Examples

**Python:**
```python
import requests

# Create story with poll
files = {'file': open('story.jpg', 'rb')}
data = {
    'account_id': 1,
    'post_type': 'story',
    'text_overlay': 'Vote now!',
    'poll_question': 'Favorite color?',
    'poll_option_1': '🔴 Red',
    'poll_option_2': '🔵 Blue'
}

response = requests.post('http://localhost:5555/api/post', 
                        files=files, data=data)
print(response.json())
```

**Node.js:**
```javascript
const FormData = require('form-data');
const fs = require('fs');

const form = new FormData();
form.append('account_id', '1');
form.append('post_type', 'carousel');
form.append('caption', 'Check out these amazing photos!');
form.append('file1', fs.createReadStream('photo1.jpg'));
form.append('file2', fs.createReadStream('photo2.jpg'));

fetch('http://localhost:5555/api/post', {
    method: 'POST',
    body: form
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 📝 Version Information

**Current Version:** 2.0.0  
**Last Updated:** July 15, 2024  
**New Features:** Stories, Carousels, Enhanced Scheduling, API Endpoints

For support or questions, check the application logs or visit the setup help page at `/setup_help`. 