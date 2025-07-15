# Instagram Automation Tool - Stories & Carousel Implementation Guide

## Overview
This document provides detailed step-by-step instructions for extending the existing Instagram automation tool to support Stories and Carousel posts in addition to regular feed posts.

## Project Structure & Requirements

### Current System Overview
- Flask web application with SQLAlchemy database
- Multi-account Instagram posting with scheduling
- Google Cloud Storage integration for media files
- Bootstrap UI with responsive design
- Test account system for development

### New Features to Implement
1. **Stories**: Photo stories with text overlays, polls, mentions, and links
2. **Carousels**: Multi-image posts (up to 20 images)
3. **Enhanced UI**: Tabbed interface for different post types
4. **Extended API**: Unified endpoints with post type parameters
5. **Advanced Scheduling**: Smart queuing and daily limits
6. **Analytics**: Comprehensive metrics tracking

---

## Phase 1: Database Schema Updates

### Step 1.1: Extend Post Model
**File**: `models.py` or equivalent database model file

**Changes Required**:
1. Add `post_type` field to Post model
   - Type: String (Enum: 'feed', 'story', 'carousel')
   - Default: 'feed'
   - Required field

2. Add `media_files` field for carousels
   - Type: JSON or Text field
   - Store array of filenames in order: `["img1.jpg", "img2.jpg", "img3.jpg"]`
   - Nullable (only used for carousels)

3. Add `story_elements` field for story interactive elements
   - Type: JSON field
   - Store structure:
   ```json
   {
     "text_overlay": {
       "text": "Hello World!",
       "position": "center", // top, center, bottom
       "style": "default" // predefined style templates
     },
     "poll": {
       "question": "What's your favorite color?",
       "options": ["Red", "Blue", "Green", "Yellow"],
       "type": "multiple_choice"
     },
     "mentions": ["@username1", "@username2"],
     "link": {
       "url": "https://example.com",
       "text": "Swipe up"
     }
   }
   ```
   - Nullable (only used for stories)

4. Add `daily_post_count` tracking
   - Add helper method to count daily posts per account
   - Include validation for 25-post daily limit

### Step 1.2: Create Supporting Tables

**New Table: StoryTemplates**
```sql
- id (Primary Key)
- template_name (String, 50 chars)
- template_type (Enum: 'text_overlay', 'poll')
- template_data (JSON)
- is_global (Boolean, default True)
- created_at (DateTime)
```

**New Table: MentionSuggestions** 
```sql
- id (Primary Key)
- username (String, 50 chars, unique)
- usage_count (Integer, default 0)
- last_used (DateTime)
- created_at (DateTime)
```

**New Table: PostMetrics** (for enhanced analytics)
```sql
- id (Primary Key)
- post_id (Foreign Key to Post)
- metric_type (Enum: 'views', 'reach', 'impressions', 'poll_responses', 'link_clicks')
- metric_value (Integer)
- recorded_at (DateTime)
```

### Step 1.3: Database Migration Script
Create migration to:
1. Add new columns to existing Post table
2. Create new supporting tables
3. Populate default values for existing posts (set post_type='feed')
4. Create indexes for performance

---

## Phase 2: Backend API Development

### Step 2.1: Update File Upload System

**File**: `app.py` - Upload route modifications

**Changes Required**:
1. **Account-Specific Folder Structure**:
   ```
   /uploads/{account_id}/feed/
   /uploads/{account_id}/stories/
   /uploads/{account_id}/carousels/
   ```

2. **Multiple File Upload Support**:
   - Accept multiple files for carousel uploads
   - Parse filenames for numeric ordering
   - Validate file types (images only for now)
   - Implement 20-image limit for carousels

3. **Filename Processing Logic**:
   ```python
   def parse_filename_order(filename):
       # Extract numbers from filename
       # Sort by numeric order if found
       # Fallback to alphabetical order
   ```

### Step 2.2: Extend Posting Logic

**File**: `instagram_api.py` or equivalent Instagram integration file

**New Functions Required**:

1. **Story Posting Function**:
   ```python
   def post_story(account, image_path, story_elements):
       # Upload image to Instagram
       # Add text overlays via Instagram API
       # Add poll elements
       # Add mentions
       # Add link if provided
       # Return story ID and metrics
   ```

2. **Carousel Posting Function**:
   ```python
   def post_carousel(account, image_paths, caption, hashtags):
       # Upload multiple images
       # Create carousel container
       # Publish carousel with caption
       # Return post ID
   ```

3. **Enhanced Metrics Collection**:
   ```python
   def collect_post_metrics(post_id, post_type):
       # Fetch metrics based on post type
       # Store in PostMetrics table
       # Return metrics dictionary
   ```

### Step 2.3: API Endpoints Development

**File**: `routes.py` or `api.py`

**New Endpoints Required**:

1. **Unified Post Creation**:
   ```
   POST /api/posts
   Content-Type: application/json
   
   Body examples:
   // Feed post
   {
     "account_id": 1,
     "post_type": "feed",
     "image": "image.jpg",
     "caption": "Hello world",
     "hashtags": ["#hello", "#world"],
     "scheduled_time": "2024-01-15T10:00:00"
   }
   
   // Story post
   {
     "account_id": 1,
     "post_type": "story",
     "image": "story.jpg",
     "story_elements": {
       "text_overlay": {"text": "Good morning!", "position": "center"},
       "poll": {"question": "How are you?", "options": ["Great", "Good", "Okay", "Not so good"]},
       "mentions": ["@friend1", "@friend2"]
     },
     "scheduled_time": "2024-01-15T08:00:00"
   }
   
   // Carousel post
   {
     "account_id": 1,
     "post_type": "carousel",
     "images": ["img1.jpg", "img2.jpg", "img3.jpg"],
     "caption": "My vacation photos",
     "hashtags": ["#vacation", "#travel"],
     "scheduled_time": "2024-01-15T12:00:00"
   }
   ```

2. **Template Management**:
   ```
   GET /api/templates/{type}        // Get templates by type
   POST /api/templates              // Create new template
   PUT /api/templates/{id}          // Update template
   DELETE /api/templates/{id}       // Delete template
   ```

3. **Mention Suggestions**:
   ```
   GET /api/mentions/suggest?q={query}  // Get mention suggestions
   POST /api/mentions                   // Add new mention
   ```

4. **Enhanced Analytics**:
   ```
   GET /api/analytics/{account_id}?type={post_type}&days={n}
   ```

### Step 2.4: Scheduling Enhancements

**File**: `scheduler.py` or equivalent

**Enhanced Logic Required**:

1. **Daily Limit Enforcement**:
   ```python
   def check_daily_limit(account_id, scheduled_date):
       # Count existing posts for the date
       # Return remaining quota (max 25)
       # Queue for next day if limit reached
   ```

2. **Story Auto-Scheduling**:
   ```python
   def auto_schedule_stories(account_id, story_count, start_date):
       # Generate 2-hour intervals between 6 AM - 2 AM
       # Assign stories to available slots
       # Handle overflow to next day
   ```

3. **Smart Queue Management**:
   ```python
   def queue_post_for_next_available_slot(account_id, post_data):
       # Find next available slot respecting daily limits
       # Maintain posting frequency rules
       # Update scheduling database
   ```

---

## Phase 3: Frontend UI Development

### Step 3.1: Main Posting Interface Redesign

**File**: `templates/index.html` or main posting template

**UI Structure**:
```html
<div class="posting-interface">
  <!-- Tab Navigation -->
  <ul class="nav nav-tabs" id="postTypeTabs">
    <li class="nav-item">
      <a class="nav-link active" data-bs-toggle="tab" href="#feedPost">
        <i class="fas fa-image"></i> Feed Post
      </a>
    </li>
    <li class="nav-item">
      <a class="nav-link" data-bs-toggle="tab" href="#storyPost">
        <i class="fas fa-circle"></i> Story
      </a>
    </li>
    <li class="nav-item">
      <a class="nav-link" data-bs-toggle="tab" href="#carouselPost">
        <i class="fas fa-images"></i> Carousel
      </a>
    </li>
  </ul>

  <!-- Tab Content -->
  <div class="tab-content" id="postTypeContent">
    <!-- Feed Post Tab -->
    <div class="tab-pane fade show active" id="feedPost">
      <!-- Existing feed post form -->
    </div>
    
    <!-- Story Tab -->
    <div class="tab-pane fade" id="storyPost">
      <!-- Story creation interface -->
    </div>
    
    <!-- Carousel Tab -->
    <div class="tab-pane fade" id="carouselPost">
      <!-- Carousel creation interface -->
    </div>
  </div>
</div>
```

### Step 3.2: Story Creation Interface

**Components Required**:

1. **Image Upload Section**:
   ```html
   <div class="story-upload-zone">
     <input type="file" id="storyImage" accept="image/*">
     <div class="upload-placeholder">
       <i class="fas fa-upload"></i>
       <p>Upload Story Image</p>
     </div>
   </div>
   ```

2. **Story Elements (Collapsible Sections)**:
   ```html
   <!-- Text Overlay Section -->
   <div class="accordion-item">
     <h2 class="accordion-header">
       <button class="accordion-button" data-bs-toggle="collapse" 
               data-bs-target="#textOverlay">
         <i class="fas fa-font"></i> Text Overlay
       </button>
     </h2>
     <div id="textOverlay" class="accordion-collapse collapse">
       <div class="accordion-body">
         <input type="text" placeholder="Enter text" id="overlayText">
         <select id="textPosition">
           <option value="top">Top</option>
           <option value="center">Center</option>
           <option value="bottom">Bottom</option>
         </select>
         <select id="textStyle">
           <option value="default">Default</option>
           <!-- Template options loaded dynamically -->
         </select>
       </div>
     </div>
   </div>

   <!-- Poll Section -->
   <div class="accordion-item">
     <h2 class="accordion-header">
       <button class="accordion-button collapsed" data-bs-toggle="collapse" 
               data-bs-target="#pollSection">
         <i class="fas fa-poll"></i> Poll
       </button>
     </h2>
     <div id="pollSection" class="accordion-collapse collapse">
       <div class="accordion-body">
         <input type="text" placeholder="Poll question" id="pollQuestion">
         <div class="poll-options">
           <input type="text" placeholder="Option 1" class="poll-option">
           <input type="text" placeholder="Option 2" class="poll-option">
           <input type="text" placeholder="Option 3" class="poll-option">
           <input type="text" placeholder="Option 4" class="poll-option">
         </div>
         <select id="pollTemplate">
           <option value="">Select template</option>
           <!-- Poll templates loaded dynamically -->
         </select>
       </div>
     </div>
   </div>

   <!-- Mentions Section -->
   <div class="accordion-item">
     <h2 class="accordion-header">
       <button class="accordion-button collapsed" data-bs-toggle="collapse" 
               data-bs-target="#mentionsSection">
         <i class="fas fa-at"></i> Mentions
       </button>
     </h2>
     <div id="mentionsSection" class="accordion-collapse collapse">
       <div class="accordion-body">
         <input type="text" id="mentionInput" placeholder="Type @ to mention">
         <div id="mentionSuggestions" class="suggestion-dropdown"></div>
         <div id="selectedMentions" class="mention-tags"></div>
       </div>
     </div>
   </div>

   <!-- Link Section -->
   <div class="accordion-item">
     <h2 class="accordion-header">
       <button class="accordion-button collapsed" data-bs-toggle="collapse" 
               data-bs-target="#linkSection">
         <i class="fas fa-link"></i> Link
       </button>
     </h2>
     <div id="linkSection" class="accordion-collapse collapse">
       <div class="accordion-body">
         <input type="url" placeholder="https://example.com" id="storyLink">
         <input type="text" placeholder="Link text" id="linkText">
       </div>
     </div>
   </div>
   ```

3. **Real-time Preview**:
   ```html
   <div class="story-preview">
     <div class="story-frame">
       <div class="story-image-container">
         <img id="previewImage" src="" alt="Story preview">
         <div id="previewTextOverlay" class="text-overlay"></div>
         <div id="previewPoll" class="poll-overlay"></div>
         <div id="previewMentions" class="mentions-overlay"></div>
         <div id="previewLink" class="link-overlay"></div>
       </div>
     </div>
   </div>
   ```

### Step 3.3: Carousel Creation Interface

**Components Required**:

1. **Multiple Image Upload**:
   ```html
   <div class="carousel-upload-zone">
     <input type="file" id="carouselImages" multiple accept="image/*" max="20">
     <div class="upload-placeholder">
       <i class="fas fa-images"></i>
       <p>Upload Carousel Images (Max 20)</p>
       <small>Images will be ordered by filename numbers</small>
     </div>
   </div>
   ```

2. **Image Reordering Interface**:
   ```html
   <div class="carousel-organizer">
     <h5>Organize Images</h5>
     <div id="carouselImageList" class="sortable-list">
       <!-- Dynamic image items with drag handles -->
       <div class="carousel-item" data-filename="img1.jpg">
         <div class="drag-handle">
           <i class="fas fa-grip-vertical"></i>
         </div>
         <img src="preview.jpg" alt="Image 1">
         <div class="item-controls">
           <button class="btn btn-sm btn-outline-primary move-up">
             <i class="fas fa-arrow-up"></i>
           </button>
           <button class="btn btn-sm btn-outline-primary move-down">
             <i class="fas fa-arrow-down"></i>
           </button>
           <button class="btn btn-sm btn-outline-danger remove">
             <i class="fas fa-trash"></i>
           </button>
         </div>
         <span class="position-indicator">1</span>
       </div>
     </div>
   </div>
   ```

3. **Carousel Preview**:
   ```html
   <div class="carousel-preview">
     <div class="preview-container">
       <div id="carouselSlider" class="carousel slide">
         <div class="carousel-inner" id="previewSlides">
           <!-- Dynamic slides generated from uploaded images -->
         </div>
         <button class="carousel-control-prev" type="button">
           <span class="carousel-control-prev-icon"></span>
         </button>
         <button class="carousel-control-next" type="button">
           <span class="carousel-control-next-icon"></span>
         </button>
       </div>
       <div class="slide-counter">
         <span id="currentSlide">1</span> / <span id="totalSlides">1</span>
       </div>
     </div>
   </div>
   ```

### Step 3.4: Enhanced Scheduling Interface

**Components Required**:

1. **Smart Scheduling Options**:
   ```html
   <div class="scheduling-options">
     <div class="row">
       <div class="col-md-6">
         <label>Scheduling Type</label>
         <select id="schedulingType" class="form-control">
           <option value="immediate">Post Now</option>
           <option value="specific">Specific Time</option>
           <option value="auto_story">Auto-Schedule Stories</option>
           <option value="queue">Add to Queue</option>
         </select>
       </div>
       <div class="col-md-6" id="specificTimeContainer" style="display: none;">
         <label>Schedule Date & Time</label>
         <input type="datetime-local" id="scheduledTime" class="form-control">
       </div>
     </div>
     
     <!-- Auto-scheduling options for stories -->
     <div id="autoScheduleOptions" style="display: none;">
       <div class="row">
         <div class="col-md-4">
           <label>Start Date</label>
           <input type="date" id="autoStartDate" class="form-control">
         </div>
         <div class="col-md-4">
           <label>Number of Stories</label>
           <input type="number" id="storyCount" class="form-control" min="1" max="10">
         </div>
         <div class="col-md-4">
           <label>Interval</label>
           <select id="storyInterval" class="form-control">
             <option value="2">Every 2 hours</option>
             <option value="3">Every 3 hours</option>
             <option value="4">Every 4 hours</option>
           </select>
         </div>
       </div>
     </div>
   </div>
   ```

2. **Daily Limit Indicator**:
   ```html
   <div class="daily-limit-status">
     <div class="limit-bar">
       <div class="limit-progress" style="width: 60%;"></div>
     </div>
     <small class="text-muted">
       <span id="postsUsed">15</span> / <span id="postsLimit">25</span> posts today
       <span id="postsRemaining">10</span> remaining
     </small>
   </div>
   ```

---

## Phase 4: JavaScript Frontend Logic

### Step 4.1: Core JavaScript Files Structure

**File Organization**:
```
static/js/
├── posting/
│   ├── base-posting.js          // Common posting functionality
│   ├── story-builder.js         // Story-specific logic
│   ├── carousel-builder.js      // Carousel-specific logic
│   └── scheduling.js            // Enhanced scheduling logic
├── templates/
│   ├── story-templates.js       // Story template management
│   └── mention-suggestions.js   // Mention auto-complete
└── preview/
    ├── story-preview.js         // Real-time story preview
    └── carousel-preview.js      // Carousel preview & reordering
```

### Step 4.2: Story Builder JavaScript

**File**: `static/js/posting/story-builder.js`

**Key Functions Required**:

1. **Image Upload & Preview**:
   ```javascript
   function handleStoryImageUpload(file) {
       // Validate image file
       // Create preview URL
       // Update preview container
       // Enable story elements
   }
   ```

2. **Text Overlay Management**:
   ```javascript
   function updateTextOverlay() {
       // Get text, position, style
       // Update preview overlay
       // Store in story elements data
   }
   
   function loadTextTemplates() {
       // Fetch available templates
       // Populate dropdown
       // Handle template selection
   }
   ```

3. **Poll Builder**:
   ```javascript
   function createPoll() {
       // Validate question and options
       // Update preview
       // Store poll data
   }
   
   function loadPollTemplates() {
       // Load predefined poll templates
       // Handle template application
   }
   ```

4. **Mention Auto-complete**:
   ```javascript
   function initMentionAutocomplete() {
       // Setup mention input listener
       // Fetch suggestions from API
       // Handle mention selection
       // Update mentions list
   }
   
   function addMention(username) {
       // Add to selected mentions
       // Update API usage count
       // Update preview
   }
   ```

5. **Real-time Preview Updates**:
   ```javascript
   function updateStoryPreview() {
       // Combine all elements
       // Position overlays correctly
       // Show interactive elements
   }
   ```

### Step 4.3: Carousel Builder JavaScript

**File**: `static/js/posting/carousel-builder.js`

**Key Functions Required**:

1. **Multiple File Upload**:
   ```javascript
   function handleCarouselUpload(files) {
       // Validate file count (max 20)
       // Validate file types
       // Parse filename ordering
       // Create preview thumbnails
       // Initialize drag-and-drop
   }
   
   function parseFilenameOrder(files) {
       // Extract numbers from filenames
       // Sort by numeric order
       // Fallback to alphabetical
       // Return ordered file list
   }
   ```

2. **Drag & Drop Reordering**:
   ```javascript
   function initDragAndDrop() {
       // Setup sortable functionality
       // Handle drag events
       // Update order indicators
       // Sync with preview slider
   }
   
   function moveImageUp(index) {
       // Swap positions
       // Update UI
       // Sync preview
   }
   
   function moveImageDown(index) {
       // Swap positions
       // Update UI
       // Sync preview
   }
   ```

3. **Preview Slider**:
   ```javascript
   function updateCarouselPreview() {
       // Generate carousel slides
       // Setup navigation
       // Add slide indicators
       // Handle slide changes
   }
   
   function removeCarouselImage(index) {
       // Remove from file list
       // Update UI
       // Regenerate preview
   }
   ```

### Step 4.4: Enhanced Scheduling JavaScript

**File**: `static/js/posting/scheduling.js`

**Key Functions Required**:

1. **Daily Limit Tracking**:
   ```javascript
   function updateDailyLimitStatus(accountId) {
       // Fetch current day's post count
       // Update progress bar
       // Show remaining quota
       // Handle limit warnings
   }
   ```

2. **Auto-scheduling Logic**:
   ```javascript
   function generateStorySchedule(startDate, count, interval) {
       // Calculate time slots (6 AM - 2 AM)
       // Generate scheduled times
       // Handle date boundaries
       // Return schedule array
   }
   
   function validateScheduleTime(dateTime, accountId) {
       // Check daily limits
       // Validate time range
       // Check for conflicts
       // Return validation result
   }
   ```

3. **Queue Management**:
   ```javascript
   function addToQueue(postData) {
       // Find next available slot
       // Check daily limits
       // Schedule for appropriate time
       // Show queue status
   }
   ```

---

## Phase 5: Template System Implementation

### Step 5.1: Story Text Templates

**Template Categories**:

1. **Position-based Templates**:
   ```json
   {
     "template_name": "Top Bold",
     "template_type": "text_overlay",
     "template_data": {
       "position": "top",
       "font_size": "large",
       "font_weight": "bold",
       "color": "white",
       "background": "semi-transparent"
     }
   }
   ```

2. **Style-based Templates**:
   ```json
   {
     "template_name": "Center Elegant",
     "template_type": "text_overlay", 
     "template_data": {
       "position": "center",
       "font_family": "serif",
       "font_size": "medium",
       "color": "black",
       "background": "white_box"
     }
   }
   ```

### Step 5.2: Poll Templates

**Template Examples**:

1. **Engagement Polls**:
   ```json
   {
     "template_name": "Like/Dislike",
     "template_type": "poll",
     "template_data": {
       "question": "What do you think?",
       "options": ["👍 Love it", "👎 Not for me", "🤔 Maybe", "💬 Tell me more"]
     }
   }
   ```

2. **Feedback Polls**:
   ```json
   {
     "template_name": "Rating Scale",
     "template_type": "poll",
     "template_data": {
       "question": "How would you rate this?",
       "options": ["⭐ Excellent", "😊 Good", "😐 Okay", "😞 Poor"]
     }
   }
   ```

3. **Choice Polls**:
   ```json
   {
     "template_name": "Preference Check",
     "template_type": "poll",
     "template_data": {
       "question": "Which do you prefer?",
       "options": ["Option A", "Option B", "Option C", "No preference"]
     }
   }
   ```

### Step 5.3: Template Management Interface

**Admin Interface Requirements**:

1. **Template Creation Form**:
   ```html
   <form id="templateForm">
     <select id="templateType">
       <option value="text_overlay">Text Overlay</option>
       <option value="poll">Poll Template</option>
     </select>
     
     <input type="text" id="templateName" placeholder="Template name">
     
     <!-- Dynamic fields based on template type -->
     <div id="templateFields"></div>
     
     <button type="submit">Save Template</button>
   </form>
   ```

2. **Template Management Page**:
   - List all templates by type
   - Edit/delete functionality
   - Preview templates
   - Usage statistics

---

## Phase 6: Analytics & Metrics Implementation

### Step 6.1: Metrics Collection System

**Metrics to Track**:

1. **Story Metrics**:
   - Views (impressions)
   - Reach (unique viewers)
   - Completion rate
   - Poll responses and percentages
   - Link clicks
   - Profile visits from story

2. **Carousel Metrics**:
   - Total reach and impressions
   - Individual slide performance
   - Swipe-through rate
   - Engagement per slide
   - Time spent on each slide

3. **Overall Account Metrics**:
   - Daily post performance comparison
   - Best performing post types
   - Optimal posting times
   - Hashtag performance by post type

### Step 6.2: Analytics Dashboard

**Dashboard Sections**:

1. **Overview Cards**:
   ```html
   <div class="analytics-overview">
     <div class="metric-card">
       <h4>Stories Today</h4>
       <span class="metric-value">8</span>
       <span class="metric-change">+2 from yesterday</span>
     </div>
     
     <div class="metric-card">
       <h4>Carousel Performance</h4>
       <span class="metric-value">85%</span>
       <span class="metric-change">Avg completion rate</span>
     </div>
   </div>
   ```

2. **Performance Charts**:
   - Line charts for story views over time
   - Bar charts for carousel slide performance
   - Pie charts for post type distribution
   - Heatmaps for optimal posting times

3. **Detailed Reports**:
   - Individual post performance
   - Template effectiveness
   - Hashtag performance by post type
   - Account comparison views

---

## Phase 7: API Documentation

### Step 7.1: Story API Documentation

**Endpoint**: `POST /api/posts` (post_type: "story")

**Request Format**:
```json
{
  "account_id": 1,
  "post_type": "story",
  "image": "story_image.jpg",
  "story_elements": {
    "text_overlay": {
      "text": "Good morning everyone!",
      "position": "center",
      "style": "bold_white"
    },
    "poll": {
      "question": "How's your day going?",
      "options": ["Amazing!", "Pretty good", "Okay", "Could be better"]
    },
    "mentions": ["@bestfriend", "@colleague"],
    "link": {
      "url": "https://mywebsite.com",
      "text": "Check this out"
    }
  },
  "scheduled_time": "2024-01-15T08:00:00Z"
}
```

**Response Format**:
```json
{
  "success": true,
  "post_id": 123,
  "message": "Story scheduled successfully",
  "scheduled_for": "2024-01-15T08:00:00Z",
  "story_url": "https://instagram.com/stories/account/123"
}
```

### Step 7.2: Carousel API Documentation

**Endpoint**: `POST /api/posts` (post_type: "carousel")

**Request Format**:
```json
{
  "account_id": 1,
  "post_type": "carousel",
  "images": [
    "vacation_1.jpg",
    "vacation_2.jpg", 
    "vacation_3.jpg"
  ],
  "caption": "Amazing vacation memories! 🌴",
  "hashtags": ["#vacation", "#travel", "#memories"],
  "scheduled_time": "2024-01-15T12:00:00Z"
}
```

**Response Format**:
```json
{
  "success": true,
  "post_id": 124,
  "message": "Carousel scheduled successfully",
  "scheduled_for": "2024-01-15T12:00:00Z",
  "post_url": "https://instagram.com/p/ABC123",
  "image_count": 3
}
```

### Step 7.3: Bulk Operations API

**Bulk Story Creation**:
```json
{
  "account_id": 1,
  "post_type": "story",
  "bulk_operation": true,
  "auto_schedule": {
    "start_date": "2024-01-15",
    "interval_hours": 2,
    "time_range": {
      "start": "06:00",
      "end": "02:00"
    }
  },
  "stories": [
    {
      "image": "story1.jpg",
      "story_elements": { /* story data */ }
    },
    {
      "image": "story2.jpg", 
      "story_elements": { /* story data */ }
    }
  ]
}
```

---

## Phase 8: Testing Strategy

### Step 8.1: Unit Testing

**Test Files to Create**:

1. **Backend Tests**:
   - `test_story_posting.py`: Test story creation, scheduling, and Instagram API integration
   - `test_carousel_posting.py`: Test carousel upload, ordering, and posting
   - `test_scheduling_logic.py`: Test daily limits, auto-scheduling, queuing
   - `test_template_system.py`: Test template CRUD operations
   - `test_analytics.py`: Test metrics collection and calculations

2. **Frontend Tests**:
   - `test_story_builder.js`: Test story UI interactions and preview
   - `test_carousel_builder.js`: Test image reordering and carousel preview
   - `test_scheduling.js`: Test scheduling interface and validations

### Step 8.2: Integration Testing

**Test Scenarios**:

1. **End-to-End Story Flow**:
   - Upload image → Add text overlay → Add poll → Schedule → Post to Instagram
   - Verify metrics collection after posting

2. **End-to-End Carousel Flow**:
   - Upload 5 images → Reorder via drag-and-drop → Add caption → Schedule → Post
   - Verify all images posted in correct order

3. **Daily Limit Testing**:
   - Schedule 25 posts for one day → Attempt 26th post → Verify queuing for next day
   - Test across multiple accounts

4. **Template System Testing**:
   - Create story template → Apply to new story → Verify correct formatting
   - Test poll templates with different question types

### Step 8.3: User Acceptance Testing

**Test Cases**:

1. **Story Creation Workflow**:
   - Non-technical user creates story with all elements
   - Verify intuitive UI and clear instructions

2. **Carousel Management**:
   - User uploads 15 images → Reorders them → Removes 3 → Publishes
   - Test drag-and-drop vs button controls

3. **Bulk Scheduling**:
   - User schedules 10 stories for auto-posting over 5 days
   - Verify correct time distribution and notifications

---

## Phase 9: Deployment Strategy

### Step 9.1: Database Migration

**Pre-deployment Steps**:
1. Backup existing database
2. Test migration script on staging environment
3. Plan rollback strategy
4. Schedule maintenance window

**Migration Script**:
```sql
-- Add new columns to Post table
ALTER TABLE posts ADD COLUMN post_type VARCHAR(20) DEFAULT 'feed';
ALTER TABLE posts ADD COLUMN media_files JSON;
ALTER TABLE posts ADD COLUMN story_elements JSON;

-- Create new tables
CREATE TABLE story_templates (...);
CREATE TABLE mention_suggestions (...);
CREATE TABLE post_metrics (...);

-- Update existing data
UPDATE posts SET post_type = 'feed' WHERE post_type IS NULL;
```

### Step 9.2: Feature Rollout Plan

**Phase 1 - Backend Only**:
- Deploy database changes
- Deploy API endpoints
- Test with API clients
- Verify existing functionality unchanged

**Phase 2 - UI Integration**:
- Deploy frontend changes
- Enable story and carousel tabs
- Test with small user group
- Monitor for issues

**Phase 3 - Full Feature Launch**:
- Enable for all users
- Announce new features
- Provide user documentation
- Monitor analytics and feedback

### Step 9.3: Monitoring & Support

**Monitoring Setup**:
1. **API Endpoint Monitoring**:
   - Track success/failure rates for new endpoints
   - Monitor response times
   - Alert on error spikes

2. **Instagram API Monitoring**:
   - Track story posting success rates
   - Monitor carousel upload failures
   - Watch for API limit violations

3. **User Behavior Analytics**:
   - Track feature adoption rates
   - Monitor user workflow completion
   - Identify common error patterns

**Support Documentation**:
1. **User Guides**:
   - How to create engaging stories
   - Best practices for carousel posts
   - Scheduling optimization tips

2. **Troubleshooting Guides**:
   - Common story posting errors
   - Carousel image ordering issues
   - Scheduling conflicts resolution

---

## Phase 10: Future Enhancements

### Step 10.1: Advanced Story Features

**Phase 2 Story Features**:
1. **Video Stories**: Support for 15-second video uploads
2. **Music Integration**: Add background music to stories
3. **Advanced Stickers**: GIF stickers, location tags, countdown timers
4. **Story Highlights**: Automatic saving to highlights
5. **Story Analytics**: Advanced metrics and insights

### Step 10.2: Carousel Enhancements

**Future Carousel Features**:
1. **Mixed Media**: Photos and videos in same carousel
2. **Individual Captions**: Different captions per carousel item
3. **Product Tags**: E-commerce integration
4. **Carousel Templates**: Predefined layouts and themes

### Step 10.3: AI-Powered Features

**Intelligent Automation**:
1. **Smart Scheduling**: AI-optimized posting times based on audience activity
2. **Content Suggestions**: AI-generated caption and hashtag recommendations
3. **Performance Optimization**: Automatic A/B testing of post variations
4. **Trend Detection**: Real-time hashtag and content trend analysis

---

## Implementation Timeline

### Week 1-2: Database & Backend Foundation
- Database schema updates and migrations
- Core API endpoint development
- Instagram API integration for stories and carousels

### Week 3-4: Frontend UI Development  
- Tabbed posting interface
- Story builder with real-time preview
- Carousel organizer with drag-and-drop

### Week 5-6: Advanced Features
- Template system implementation
- Enhanced scheduling logic
- Mention auto-complete system

### Week 7-8: Analytics & Polish
- Metrics collection and dashboard
- Error handling and validation
- Performance optimization

### Week 9-10: Testing & Deployment
- Comprehensive testing suite
- User acceptance testing
- Production deployment and monitoring

---

## Success Metrics

### Technical Metrics
- **API Performance**: <200ms response time for all endpoints
- **Upload Success Rate**: >99% for image uploads
- **Instagram API Success**: >95% posting success rate
- **UI Responsiveness**: <100ms for all user interactions

### User Experience Metrics
- **Feature Adoption**: >80% of users try new story/carousel features within 30 days
- **User Retention**: Maintain current retention rates with new features
- **Error Rate**: <1% user-reported errors
- **Satisfaction Score**: >4.5/5 user satisfaction rating

### Business Metrics
- **Post Volume**: 300% increase in total posts (stories + carousels + feed)
- **User Engagement**: 50% increase in daily active users
- **Feature Usage**: 70% of users regularly use stories, 40% use carousels
- **Account Growth**: 25% increase in connected Instagram accounts

This comprehensive implementation guide provides the detailed roadmap for successfully extending the Instagram automation tool with Stories and Carousel functionality while maintaining the existing system's reliability and performance.
