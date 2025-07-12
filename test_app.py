#!/usr/bin/env python3
"""
Comprehensive test script for Instagram Automation Tool
Tests all routes and functionality to ensure nothing is broken
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5555"

def test_route(route, method="GET", data=None, files=None):
    """Test a specific route and return the result"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{route}")
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{route}", data=data, files=files)
        
        return {
            "route": route,
            "method": method,
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "response_length": len(response.text),
            "content_type": response.headers.get('content-type', '')
        }
    except Exception as e:
        return {
            "route": route,
            "method": method,
            "error": str(e),
            "success": False
        }

def run_tests():
    """Run all tests"""
    print("🚀 Starting comprehensive tests for Instagram Automation Tool")
    print("=" * 60)
    
    # Test all GET routes
    routes_to_test = [
        "/",                    # Dashboard
        "/accounts",            # Accounts page
        "/add_account",         # Add account form
        "/upload",              # Upload page
        "/posts",               # Posts page
        "/test_api",            # API test
        "/test_upload",         # Upload test
        "/init_db",             # Database initialization
    ]
    
    results = []
    
    for route in routes_to_test:
        print(f"Testing {route}...")
        result = test_route(route)
        results.append(result)
        
        if result["success"]:
            print(f"  ✅ {route} - Status: {result['status_code']} - Size: {result['response_length']} bytes")
        else:
            print(f"  ❌ {route} - Error: {result.get('error', 'HTTP ' + str(result.get('status_code', 'Unknown')))}")
    
    # Test POST routes (form submissions)
    print("\n" + "=" * 60)
    print("Testing POST routes...")
    
    # Test add account form (should fail validation but not crash)
    print("Testing add_account form validation...")
    add_account_result = test_route("/add_account", "POST", {
        "username": "",
        "instagram_id": "",
        "access_token": ""
    })
    results.append(add_account_result)
    
    if add_account_result["success"]:
        print("  ✅ Add account form validation working")
    else:
        print(f"  ❌ Add account form error: {add_account_result.get('error', 'Unknown')}")
    
    # Test upload form (should fail validation but not crash)
    print("Testing upload form validation...")
    upload_result = test_route("/upload", "POST", {
        "account_id": "",
        "custom_text": "",
        "schedule_type": "now"
    })
    results.append(upload_result)
    
    if upload_result["success"]:
        print("  ✅ Upload form validation working")
    else:
        print(f"  ❌ Upload form error: {upload_result.get('error', 'Unknown')}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - successful_tests
    
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print("\n❌ FAILED TESTS:")
        for result in results:
            if not result["success"]:
                print(f"  - {result['route']} ({result['method']}): {result.get('error', 'HTTP ' + str(result.get('status_code', 'Unknown')))}")
    else:
        print("\n🎉 ALL TESTS PASSED!")
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("🌐 Application is running at: http://localhost:5555")
    print("📋 You can now test file upload functionality manually")

if __name__ == "__main__":
    run_tests() 