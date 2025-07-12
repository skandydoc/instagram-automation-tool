#!/usr/bin/env python3
"""
Instagram Test Account Generator
Generates hundreds of test accounts for infrastructure load testing
"""

import random
import string
import uuid
from datetime import datetime, timedelta
import json
import time

class TestAccountGenerator:
    """Generator for creating test Instagram accounts for load testing"""
    
    def __init__(self):
        self.account_types = ['business', 'creator', 'personal']
        self.niches = [
            'fitness', 'food', 'travel', 'fashion', 'technology', 'lifestyle',
            'beauty', 'sports', 'music', 'art', 'photography', 'education',
            'health', 'business', 'entertainment', 'nature', 'cars', 'pets',
            'gaming', 'books', 'movies', 'cooking', 'yoga', 'motivation'
        ]
        self.username_prefixes = [
            'test_', 'demo_', 'sample_', 'mock_', 'dev_', 'staging_',
            'qa_', 'load_', 'perf_', 'bulk_', 'sim_', 'auto_'
        ]
        
    def generate_test_username(self, index=None):
        """Generate a test username"""
        prefix = random.choice(self.username_prefixes)
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        if index:
            return f"{prefix}{index}_{suffix}"
        return f"{prefix}{suffix}"
    
    def generate_test_instagram_id(self):
        """Generate a test Instagram ID (17-18 digit number)"""
        return f"test{random.randint(10**14, 10**15)}"
    
    def generate_test_access_token(self, account_type='test'):
        """Generate a test access token"""
        if account_type == 'test':
            return f"test_token_{uuid.uuid4().hex[:16]}"
        else:
            # For mixed testing with some real-looking tokens
            return f"EAATesting{uuid.uuid4().hex[:32]}"
    
    def generate_single_account(self, index=None, account_type='test'):
        """Generate a single test account"""
        username = self.generate_test_username(index)
        
        account = {
            'username': username,
            'instagram_id': self.generate_test_instagram_id(),
            'access_token': self.generate_test_access_token(account_type),
            'account_type': random.choice(self.account_types),
            'niche': random.choice(self.niches),
            'is_active': True,
            'follower_count': random.randint(1000, 100000),
            'following_count': random.randint(100, 5000),
            'posts_count': random.randint(50, 2000),
            'engagement_rate': round(random.uniform(0.5, 8.0), 2),
            'created_at': datetime.now().isoformat(),
            'last_post_time': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            'status': 'active',
            'test_account': True,
            'load_test_batch': f"batch_{index // 50 + 1}" if index else "batch_1"
        }
        
        return account
    
    def generate_bulk_accounts(self, count=100, account_type='test'):
        """Generate bulk test accounts"""
        print(f"🔄 Generating {count} test accounts...")
        
        accounts = []
        for i in range(count):
            account = self.generate_single_account(i + 1, account_type)
            accounts.append(account)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"   Generated {i + 1}/{count} accounts...")
        
        print(f"✅ Generated {len(accounts)} test accounts successfully!")
        return accounts
    
    def generate_mixed_accounts(self, total_count=200, real_account_percentage=10):
        """Generate mixed accounts (test + real for validation)"""
        print(f"🔄 Generating {total_count} mixed accounts...")
        print(f"   📊 Mix: {100-real_account_percentage}% test accounts, {real_account_percentage}% real-like accounts")
        
        real_count = int(total_count * real_account_percentage / 100)
        test_count = total_count - real_count
        
        accounts = []
        
        # Generate test accounts
        for i in range(test_count):
            account = self.generate_single_account(i + 1, 'test')
            accounts.append(account)
        
        # Generate real-like accounts (for API validation)
        for i in range(real_count):
            account = self.generate_single_account(test_count + i + 1, 'real')
            account['test_account'] = False
            account['requires_real_token'] = True
            accounts.append(account)
        
        print(f"✅ Generated {len(accounts)} mixed accounts!")
        print(f"   📊 Test accounts: {test_count}")
        print(f"   📊 Real-like accounts: {real_count}")
        
        return accounts
    
    def generate_load_test_scenarios(self, account_count=100):
        """Generate different load test scenarios"""
        scenarios = {
            'light_load': {
                'accounts': account_count,
                'posts_per_account_per_day': 1,
                'concurrent_posts': 5,
                'description': 'Light load - 1 post per account per day'
            },
            'medium_load': {
                'accounts': account_count,
                'posts_per_account_per_day': 2,
                'concurrent_posts': 10,
                'description': 'Medium load - 2 posts per account per day'
            },
            'heavy_load': {
                'accounts': account_count,
                'posts_per_account_per_day': 5,
                'concurrent_posts': 20,
                'description': 'Heavy load - 5 posts per account per day'
            },
            'stress_test': {
                'accounts': account_count,
                'posts_per_account_per_day': 10,
                'concurrent_posts': 50,
                'description': 'Stress test - 10 posts per account per day'
            }
        }
        
        return scenarios
    
    def save_accounts_to_file(self, accounts, filename='test_accounts.json'):
        """Save generated accounts to file"""
        with open(filename, 'w') as f:
            json.dump(accounts, f, indent=2)
        print(f"💾 Saved {len(accounts)} accounts to {filename}")
    
    def save_accounts_to_sql(self, accounts, filename='test_accounts.sql'):
        """Generate SQL INSERT statements for bulk account creation"""
        sql_statements = []
        
        for account in accounts:
            sql = f"""
INSERT INTO accounts (username, instagram_id, access_token, account_type, niche, is_active, created_at, updated_at)
VALUES ('{account['username']}', '{account['instagram_id']}', '{account['access_token']}', 
        '{account['account_type']}', '{account['niche']}', {account['is_active']}, 
        '{account['created_at']}', '{account['created_at']}');
"""
            sql_statements.append(sql.strip())
        
        with open(filename, 'w') as f:
            f.write('\n'.join(sql_statements))
        
        print(f"💾 Generated SQL file: {filename}")
        return sql_statements
    
    def create_performance_test_plan(self, accounts):
        """Create a performance test plan"""
        plan = {
            'test_configuration': {
                'total_accounts': len(accounts),
                'test_accounts': len([a for a in accounts if a.get('test_account', True)]),
                'real_accounts': len([a for a in accounts if not a.get('test_account', True)]),
                'estimated_daily_posts': len(accounts) * 2,  # 2 posts per account per day
                'estimated_api_calls_per_hour': len(accounts) * 4,  # 4 API calls per account per hour
                'rate_limit_buffer': '50%'  # Stay within 50% of rate limits
            },
            'test_phases': [
                {
                    'phase': 'warm_up',
                    'duration': '30 minutes',
                    'accounts': min(10, len(accounts)),
                    'posts_per_account': 1,
                    'description': 'Warm-up with small subset'
                },
                {
                    'phase': 'ramp_up',
                    'duration': '1 hour',
                    'accounts': min(50, len(accounts)),
                    'posts_per_account': 2,
                    'description': 'Gradually increase load'
                },
                {
                    'phase': 'full_load',
                    'duration': '2 hours',
                    'accounts': len(accounts),
                    'posts_per_account': 2,
                    'description': 'Full load testing'
                },
                {
                    'phase': 'stress_test',
                    'duration': '30 minutes',
                    'accounts': len(accounts),
                    'posts_per_account': 5,
                    'description': 'Stress test with high load'
                }
            ],
            'monitoring_points': [
                'Database connection pool usage',
                'Background job queue size',
                'Memory usage',
                'Response times',
                'Error rates',
                'API rate limit usage'
            ]
        }
        
        return plan

def main():
    """Main function to generate test accounts"""
    generator = TestAccountGenerator()
    
    print("🎯 INSTAGRAM LOAD TESTING ACCOUNT GENERATOR")
    print("=" * 60)
    
    # Generate different account sets
    scenarios = {
        'small_test': 50,
        'medium_test': 200,
        'large_test': 500,
        'stress_test': 1000
    }
    
    print("\n📊 Available Test Scenarios:")
    for scenario, count in scenarios.items():
        print(f"   {scenario}: {count} accounts")
    
    # Generate medium test scenario (200 accounts)
    print(f"\n🚀 Generating Medium Test Scenario (200 accounts)...")
    accounts = generator.generate_mixed_accounts(200, real_account_percentage=10)
    
    # Save to different formats
    generator.save_accounts_to_file(accounts, 'test_accounts_200.json')
    generator.save_accounts_to_sql(accounts, 'test_accounts_200.sql')
    
    # Generate performance test plan
    test_plan = generator.create_performance_test_plan(accounts)
    
    with open('performance_test_plan.json', 'w') as f:
        json.dump(test_plan, f, indent=2)
    
    print(f"\n📋 Performance Test Plan Generated:")
    print(f"   📊 Total Accounts: {test_plan['test_configuration']['total_accounts']}")
    print(f"   📊 Test Accounts: {test_plan['test_configuration']['test_accounts']}")
    print(f"   📊 Real Accounts: {test_plan['test_configuration']['real_accounts']}")
    print(f"   📊 Estimated Daily Posts: {test_plan['test_configuration']['estimated_daily_posts']}")
    print(f"   📊 Estimated API Calls/Hour: {test_plan['test_configuration']['estimated_api_calls_per_hour']}")
    
    print(f"\n🎉 Test Setup Complete!")
    print(f"   📁 Files Generated:")
    print(f"      - test_accounts_200.json")
    print(f"      - test_accounts_200.sql")
    print(f"      - performance_test_plan.json")
    
    print(f"\n🔄 Next Steps:")
    print(f"   1. Review generated accounts")
    print(f"   2. Load accounts into database")
    print(f"   3. Run performance tests")
    print(f"   4. Monitor system performance")

if __name__ == "__main__":
    main() 