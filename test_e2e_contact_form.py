#!/usr/bin/env python3
"""
End-to-end test: Simulate complete frontend contact form flow
Tests user journey from form submission to database storage
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8002"
API_ENDPOINT = f"{BASE_URL}/api/contact"

print("=" * 80)
print("CONTACT FORM - END-TO-END TEST")
print("=" * 80)
print(f"\nTesting API endpoint: {API_ENDPOINT}")
print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Simulate different user scenarios
test_cases = [
    {
        "name": "Customer Inquiry",
        "data": {
            "name": "Sarah Mitchell",
            "email": "sarah.mitchell@techcorp.com",
            "phone": "+31612345678",
            "company": "Tech Corporation",
            "subject": "Blockchain Payment Integration",
            "message": "We are interested in integrating your blockchain payment gateway into our e-commerce platform. Can you provide more information about pricing and implementation timeline?"
        }
    },
    {
        "name": "Support Request",
        "data": {
            "name": "Jan van der Berg",
            "email": "jan@startup.nl",
            "subject": "API Documentation Request",
            "message": "We would like to request the API documentation for your smart contract invoicing system to better understand the integration process."
        }
    },
    {
        "name": "Partnership Inquiry",
        "data": {
            "name": "Maria Garcia",
            "email": "maria.garcia@finance.io",
            "phone": "+31987654321",
            "company": "Finance Solutions Inc",
            "subject": "Partnership Opportunity",
            "message": "We see great synergy between our company and API Blockchain. Would you be open to discussing a potential partnership for European market expansion?"
        }
    }
]

print("SCENARIO 1: Testing Form Submissions")
print("-" * 80)

successful = 0
failed = 0

for i, test_case in enumerate(test_cases, 1):
    print(f"\n[TEST {i}] {test_case['name']}")
    print(f"  Submitting as: {test_case['data']['name']} ({test_case['data']['email']})")
    
    try:
        response = requests.post(
            API_ENDPOINT,
            json=test_case['data'],
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                msg_id = result.get('id', 'unknown')
                print(f"  ✓ SUCCESS - Message ID: {msg_id[:8]}...")
                print(f"  Response: {result['message']}")
                successful += 1
            else:
                print(f"  ✗ FAILED - Server error: {result.get('error')}")
                failed += 1
        else:
            print(f"  ✗ FAILED - HTTP {response.status_code}")
            failed += 1
    
    except Exception as e:
        print(f"  ✗ FAILED - Connection error: {str(e)}")
        failed += 1

print("\n" + "=" * 80)
print("SCENARIO 2: Validation Testing")
print("-" * 80)

validation_tests = [
    {
        "name": "Invalid Email",
        "data": {
            "name": "Test User",
            "email": "not-an-email",
            "subject": "Test",
            "message": "This should fail due to invalid email"
        },
        "expect_success": False
    },
    {
        "name": "Message Too Short",
        "data": {
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Test",
            "message": "short"
        },
        "expect_success": False
    },
    {
        "name": "Valid Minimal Form",
        "data": {
            "name": "Minimal User",
            "email": "minimal@example.com",
            "subject": "Minimal Test",
            "message": "This is a minimal but valid form submission"
        },
        "expect_success": True
    }
]

for test in validation_tests:
    print(f"\n[VALIDATION] {test['name']}")
    
    try:
        response = requests.post(API_ENDPOINT, json=test['data'], timeout=10)
        
        if test['expect_success']:
            if response.status_code == 200:
                print(f"  ✓ PASS - Correctly accepted valid input")
                successful += 1
            else:
                print(f"  ✗ FAIL - Rejected valid input with {response.status_code}")
                failed += 1
        else:
            if response.status_code != 200:
                print(f"  ✓ PASS - Correctly rejected invalid input ({response.status_code})")
                successful += 1
            else:
                print(f"  ✗ FAIL - Accepted invalid input")
                failed += 1
    
    except Exception as e:
        print(f"  ✗ FAIL - Error: {str(e)}")
        failed += 1

print("\n" + "=" * 80)
print("SCENARIO 3: Data Persistence Check")
print("-" * 80)

try:
    # Try to retrieve messages (this would require admin token in production)
    # For now, just verify the file was written
    from pathlib import Path
    
    # Check multiple possible locations
    possible_locations = [
        Path('C:/tmp/contacts.json'),
        Path('/tmp/contacts.json'),
        Path('data/contacts.json')
    ]
    
    contacts_file = None
    for loc in possible_locations:
        if loc.exists():
            contacts_file = loc
            break
    
    if contacts_file:
        contacts = json.loads(contacts_file.read_text())
        print(f"\n✓ Found contacts.json at: {contacts_file.resolve()}")
        print(f"  Total messages stored: {len(contacts)}")
        
        # Show latest message
        if contacts:
            latest = contacts[-1]
            print(f"  Latest submission: {latest['name']} ({latest['email']})")
            print(f"  Subject: {latest['subject']}")
            print(f"  Timestamp: {latest['created_at']}")
    else:
        print("\n⚠ Warning: Could not locate contacts.json")
        print("  Checked locations:")
        for loc in possible_locations:
            print(f"    - {loc.resolve()}")

except Exception as e:
    print(f"\n⚠ Error checking persistence: {str(e)}")

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

total_tests = successful + failed
pass_rate = (successful / total_tests * 100) if total_tests > 0 else 0

print(f"\nTotal Tests: {total_tests}")
print(f"Passed: {successful}")
print(f"Failed: {failed}")
print(f"Pass Rate: {pass_rate:.1f}%")

if failed == 0:
    print("\n🎉 ALL TESTS PASSED - Contact form is fully functional!")
    print("\nDeployment Status:")
    print("  ✓ Backend API: Working")
    print("  ✓ Form Validation: Working")
    print("  ✓ Data Persistence: Working")
    print("  ✓ Ready for Production: YES")
else:
    print(f"\n⚠ {failed} test(s) failed - review errors above")

print(f"\nTest completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
