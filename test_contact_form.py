#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the contact form endpoint.
Tests the /api/contact POST endpoint.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8002"  # Change to your API URL
CONTACT_ENDPOINT = f"{BASE_URL}/api/contact"

def test_contact_form_valid():
    """Test valid contact form submission"""
    print("\n[TEST 1] Valid Contact Form Submission")
    
    payload = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+31652824245",
        "company": "Acme Corporation",
        "subject": "Integration Request",
        "message": "We would like to integrate your blockchain payment gateway into our platform. Can we schedule a meeting?",
        "to": "info@apiblockchain.io"
    }
    
    try:
        response = requests.post(CONTACT_ENDPOINT, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("[PASS] Contact message submitted successfully")
                return True
            else:
                print(f"[FAIL] {data.get('error')}")
                return False
        else:
            print(f"[FAIL] Unexpected status code {response.status_code}")
            return False
    
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return False


def test_contact_form_invalid_email():
    """Test with invalid email"""
    print("\n[TEST 2] Invalid Email Address")
    
    payload = {
        "name": "Jane Smith",
        "email": "not-an-email",  # Invalid email
        "subject": "Test Subject",
        "message": "This is a test message with sufficient length"
    }
    
    try:
        response = requests.post(CONTACT_ENDPOINT, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("[PASS] Invalid email rejected as expected")
            return True
        else:
            print(f"[WARN] Expected 400, got {response.status_code}")
            return False
    
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return False


def test_contact_form_short_message():
    """Test with message too short"""
    print("\n[TEST 3] Message Too Short")
    
    payload = {
        "name": "Bob Johnson",
        "email": "bob@example.com",
        "subject": "Short",
        "message": "Too short"  # Less than 10 characters after strip
    }
    
    try:
        response = requests.post(CONTACT_ENDPOINT, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("[PASS] Short message rejected as expected")
            return True
        else:
            print(f"[WARN] Expected 400, got {response.status_code}")
            return False
    
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return False


def test_contact_form_missing_required():
    """Test with missing required fields"""
    print("\n[TEST 4] Missing Required Fields")
    
    payload = {
        "name": "Alice",
        "email": "alice@example.com"
        # Missing subject and message
    }
    
    try:
        response = requests.post(CONTACT_ENDPOINT, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code != 200:
            print("[PASS] Missing fields rejected as expected")
            return True
        else:
            print(f"[WARN] Expected non-200 status, got {response.status_code}")
            return False
    
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return False


def test_contact_form_optional_fields():
    """Test with optional fields omitted"""
    print("\n[TEST 5] Minimal Contact Form (No Optional Fields)")
    
    payload = {
        "name": "Charlie Brown",
        "email": "charlie@example.com",
        "subject": "Support Question",
        "message": "I have a question about your services and would like more information"
    }
    
    try:
        response = requests.post(CONTACT_ENDPOINT, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("[PASS] Minimal form submitted successfully")
                return True
            else:
                print(f"[FAIL] {data.get('error')}")
                return False
        else:
            print(f"[FAIL] Unexpected status code {response.status_code}")
            return False
    
    except Exception as e:
        print(f"[FAIL] {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("CONTACT FORM API TEST SUITE")
    print("=" * 70)
    print(f"Testing endpoint: {CONTACT_ENDPOINT}")
    print(f"Time: {datetime.now().isoformat()}")
    
    results = {
        "Valid Submission": test_contact_form_valid(),
        "Invalid Email": test_contact_form_invalid_email(),
        "Short Message": test_contact_form_short_message(),
        "Missing Fields": test_contact_form_missing_required(),
        "Optional Fields": test_contact_form_optional_fields()
    }
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll tests passed!")
    else:
        print(f"\n{total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
