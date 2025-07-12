# 🚀 Instagram Load Testing Guide: Testing Hundreds of Accounts in Developer Mode

## 📊 Overview
This comprehensive guide shows you how to test your Instagram automation infrastructure with hundreds of accounts while staying in developer mode and respecting Instagram Graph API limits.

## 🎯 Strategy: Mixed Account Approach

### 📈 **Recommended Account Mix for Testing:**
- **90% Test Accounts** (mock accounts) - For infrastructure load testing
- **10% Real Accounts** (with valid tokens) - For API validation
- **Total Target**: 100-1000 accounts for comprehensive testing

### 🔍 **Why This Strategy Works:**
- **Test accounts bypass Instagram API rate limits** (mock API calls)
- **Real accounts validate actual API integration** (limited use)
- **Infrastructure gets tested with realistic load** (database, scheduling, memory)
- **Stays within developer mode limitations** (no app review needed)

## 📚 Instagram Graph API Rate Limits (2024)

| **Limit Type** | **Current Limit** | **Impact** |
|---------------|------------------|------------|
| Platform Rate Limits | 200 calls/hour per app | Affects real accounts only |
| Daily Post Limits | 25 posts/account/day | Real accounts only |
| Business Use Case | 4,800 × impressions/24h | Based on engagement |
| Error Codes | 429, Code 4, Code 17 | Rate limit indicators |

## 🛠️ Step-by-Step Implementation

### Step 1: Generate Test Accounts

```bash
# Run the test account generator
source venv/bin/activate
python test_account_generator.py
```

**What this creates:**
- `test_accounts_200.json` - 200 test accounts (180 test + 20 real-like)
- `test_accounts_200.sql` - SQL import file
- `performance_test_plan.json` - Testing roadmap

### Step 2: Load Accounts via Web Interface

1. **Start the application:**
   ```bash
   source venv/bin/activate
   python app.py
   ```

2. **Access Bulk Account Creation:**
   - Go to: `http://localhost:5555/bulk_accounts`
   - Set account count: 100-500 (start small)
   - Set real account percentage: 10%
   - Click "Create Bulk Accounts"

3. **Monitor the process:**
   - Watch for success messages
   - Check database for created accounts
   - Verify posting schedules are created

### Step 3: Load Test Dashboard

**Access:** `http://localhost:5555/load_test_dashboard`

**Real-time monitoring:**
- **Account Statistics**: Total, test, real, active accounts
- **Post Statistics**: Total, scheduled, posted, failed posts
- **Performance Metrics**: CPU, memory, disk usage
- **Success Rates**: Post success percentage
- **Live System Metrics**: Updates every 5 seconds

### Step 4: Run Stress Tests

**Access:** `http://localhost:5555/stress_test`

**Pre-configured scenarios:**
```
Light Load:    10 accounts, 1 post,  3 threads
Medium Load:   25 accounts, 2 posts, 10 threads  
Heavy Load:    50 accounts, 3 posts, 20 threads
Stress Test:   100 accounts, 5 posts, 50 threads
```

**Custom Configuration:**
- Number of test accounts: 1-100
- Posts per account: 1-10
- Concurrent threads: 1-50
- Test duration: 30-300 seconds

## 📈 Recommended Testing Progression

### Phase 1: Warm-Up (30 minutes)
- **Accounts**: 10 test accounts
- **Load**: 1 post per account
- **Concurrency**: 3 threads
- **Goal**: Verify basic functionality

### Phase 2: Ramp-Up (1 hour)
- **Accounts**: 50 test accounts
- **Load**: 2 posts per account
- **Concurrency**: 10 threads
- **Goal**: Test moderate load

### Phase 3: Full Load (2 hours)
- **Accounts**: 200 test accounts
- **Load**: 2 posts per account
- **Concurrency**: 20 threads
- **Goal**: Test full infrastructure

### Phase 4: Stress Test (30 minutes)
- **Accounts**: 500 test accounts
- **Load**: 5 posts per account
- **Concurrency**: 50 threads
- **Goal**: Find breaking points

## 📊 Performance Monitoring

### Key Metrics to Monitor:

1. **System Performance:**
   - CPU usage (keep below 80%)
   - Memory usage (keep below 80%)
   - Disk I/O and database size

2. **Application Performance:**
   - Post success rate (target 95%+)
   - Background job queue size
   - Response times

3. **Database Performance:**
   - Query response times
   - Connection pool usage
   - Table sizes and indexes

### API Rate Limit Monitoring:

```javascript
// Automatic API monitoring (built into dashboard)
{
  "current_api_calls": "25/200 per hour",
  "platform_rate_limit": "12.5%",
  "daily_post_limit": "10/25 per account",
  "status": "within_limits"
}
```

## 🔧 Best Practices for Load Testing

### ✅ Safe Practices:
- **Start small**: Begin with 50-100 accounts
- **Gradual scaling**: Increase load incrementally
- **Monitor resources**: Watch CPU, memory, database
- **Use test accounts**: 90% test accounts for safety
- **Off-peak testing**: Test during low-traffic hours
- **Clean up data**: Remove test data after testing

### ⚠️ Safety Guidelines:
- **Real account limits**: Keep under 10% for validation only
- **Concurrent limits**: Stay below 50 concurrent threads
- **Duration limits**: Limit stress tests to 5 minutes max
- **Resource monitoring**: Stop if CPU/memory > 80%
- **Error handling**: Monitor and respond to errors quickly

## 📋 Testing Checklist

### Pre-Testing Setup:
- [ ] Install dependencies (`psutil>=5.9.0`)
- [ ] Generate test accounts (200+ recommended)
- [ ] Configure monitoring tools
- [ ] Set up performance baselines
- [ ] Prepare cleanup procedures

### During Testing:
- [ ] Monitor system resources continuously
- [ ] Track success/failure rates
- [ ] Log performance metrics
- [ ] Watch for error patterns
- [ ] Test different load scenarios

### Post-Testing Analysis:
- [ ] Analyze performance data
- [ ] Identify bottlenecks
- [ ] Document findings
- [ ] Clean up test data
- [ ] Optimize based on results

## 💡 Advanced Testing Scenarios

### Scenario 1: High-Volume Daily Posting
```
Accounts: 500 test accounts
Posts: 2 posts per account per day (1000 total)
Schedule: Distributed across 1 PM and 10 PM slots
API Impact: ~2000 API calls per day (test accounts = 0 real calls)
```

### Scenario 2: Concurrent Peak Load
```
Accounts: 200 test accounts
Burst: 5 posts each in 1-minute window
Concurrency: 50 simultaneous posts
Database Impact: High write load testing
```

### Scenario 3: Mixed Real/Test Validation
```
Test Accounts: 180 (mock API calls)
Real Accounts: 20 (real API calls, within limits)
Validation: API integration while staying under rate limits
```

## 🎯 Expected Performance Benchmarks

### Small Scale (100 accounts):
- **Daily Posts**: 200 posts
- **API Calls**: 400 calls/hour (test accounts = 0 real calls)
- **Database**: < 10MB growth per day
- **Memory**: < 2GB peak usage
- **CPU**: < 50% average usage

### Medium Scale (500 accounts):
- **Daily Posts**: 1000 posts
- **API Calls**: 2000 calls/hour (test accounts = 0 real calls)
- **Database**: < 50MB growth per day
- **Memory**: < 8GB peak usage
- **CPU**: < 70% average usage

### Large Scale (1000 accounts):
- **Daily Posts**: 2000 posts
- **API Calls**: 4000 calls/hour (test accounts = 0 real calls)
- **Database**: < 100MB growth per day
- **Memory**: < 16GB peak usage
- **CPU**: < 80% average usage

## 🚨 Troubleshooting Common Issues

### High Memory Usage:
```python
# Optimize database connections
# Implement connection pooling
# Clean up old posts regularly
```

### Slow Database Performance:
```sql
-- Add indexes for common queries
CREATE INDEX idx_posts_account_scheduled ON posts(account_id, scheduled_time);
CREATE INDEX idx_posts_status ON posts(status);
```

### Background Job Overload:
```python
# Limit concurrent jobs
# Implement job batching
# Add job prioritization
```

## 📞 Quick Start Commands

```bash
# 1. Install dependencies
pip install psutil>=5.9.0

# 2. Generate test accounts
python test_account_generator.py

# 3. Start application
python app.py

# 4. Access load testing (browser)
open http://localhost:5555/load_test_dashboard

# 5. Create bulk accounts
# Go to: Bulk Accounts → Create 200 accounts

# 6. Run stress test
# Go to: Stress Test → Run Medium Load scenario

# 7. Monitor performance
# Dashboard auto-refreshes every 5 seconds
```

## 🎉 Success Criteria

Your infrastructure is ready for production when:

- ✅ **Successfully handles 500+ test accounts**
- ✅ **Maintains 95%+ post success rate**
- ✅ **CPU usage stays below 80% under load**
- ✅ **Memory usage remains stable**
- ✅ **Database performs well with concurrent access**
- ✅ **Background jobs process efficiently**
- ✅ **Error handling works gracefully**

## 📚 Additional Resources

- **Load Test Dashboard**: Real-time monitoring and metrics
- **Stress Test Interface**: Customizable load testing scenarios  
- **Performance API**: `/api/performance_metrics` for custom monitoring
- **Test Account Generator**: Automated bulk account creation
- **Instagram Graph API Documentation**: Official rate limit guidelines

---

**🔗 Quick Navigation:**
- [Load Test Dashboard](http://localhost:5555/load_test_dashboard)
- [Bulk Account Creation](http://localhost:5555/bulk_accounts)
- [Stress Testing](http://localhost:5555/stress_test)
- [Setup Help](http://localhost:5555/setup_help)

**Ready to test your infrastructure? Start with the Load Test Dashboard!** 🚀 