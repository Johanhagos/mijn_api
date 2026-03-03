"""
Test script for email verification endpoint (Item 8)
"""

import requests
import json
import sys
import codecs

# Fix encoding on Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from db import SessionLocal
from models_phase1 import User, Organization
from auth import create_email_verification_token, hash_token

BASE_URL = "http://localhost:5000"

def test_email_verification():
    """Test the email verification flow"""
    
    print("\n" + "="*60)
    print("[TEST] Testing Email Verification Endpoint (Item 8)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 1. Create a test user with unverified email
        print("\n[STEP 1] Creating test user with unverified email...")
        
        # Get admin org
        org = db.query(Organization).filter(Organization.slug == "demo").first()
        if not org:
            print("[ERROR] Demo organization not found. Run: python quickstart_sqlite.py")
            return False
        
        # Check if test user exists, delete if so
        test_user = db.query(User).filter(User.email == "test-verify@example.com").first()
        if test_user:
            db.delete(test_user)
            db.commit()
            print("   [INFO] Found existing test user, deleted it")
        
        # Create new test user with unverified email
        test_user = User(
            org_id=org.id,
            email="test-verify@example.com",
            password_hash="hashed_password_placeholder",
            name="Test Verification",
            role="user",
            email_verified=False,
            email_verified_at=None
        )
        db.add(test_user)
        db.flush()
        
        # 2. Generate verification token
        print("\n[STEP 2] Generating email verification token...")
        token, token_hash = create_email_verification_token()
        test_user.email_verification_token = token_hash
        test_user.email_verification_expires = datetime.now(timezone.utc) + timedelta(days=7)
        db.commit()
        
        print(f"   [OK] Token created (hash stored in DB)")
        print(f"   Token (for testing): {token[:20]}... (truncated)")
        
        # 3. Request email verification
        print("\n[STEP 3] Calling POST /auth/verify-email endpoint...")
        
        verification_payload = {
            "email": "test-verify@example.com",
            "token": token
        }
        
        response = requests.post(
            f"{BASE_URL}/auth/verify-email",
            json=verification_payload,
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Email verified successfully!")
            print(f"   Email: {result['user']['email']}")
            print(f"   Email verified: {result['user']['email_verified']}")
            print(f"   Verified at: {result['user']['email_verified_at']}")
            print(f"   Message: {result['message']}")
            
            # 4. Verify in database
            print("\n[STEP 4] Verifying in database...")
            db.refresh(test_user)
            if test_user.email_verified and test_user.email_verification_token is None:
                print("   [OK] Database correctly updated!")
                print("   - email_verified = True")
                print("   - email_verification_token = None")
                print("\n[SUCCESS] EMAIL VERIFICATION FLOW COMPLETED SUCCESSFULLY!")
                return True
            else:
                print("   [ERROR] Database not updated correctly")
                return False
        else:
            print(f"   [ERROR] Request failed")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_invalid_token():
    """Test verification with invalid token"""
    
    print("\n" + "="*60)
    print("[TEST] Testing Invalid Token Rejection")
    print("="*60)
    
    try:
        print("\n[STEP 1] Calling with invalid token...")
        
        payload = {
            "email": "test-verify@example.com",
            "token": "invalid-token-should-fail"
        }
        
        response = requests.post(
            f"{BASE_URL}/auth/verify-email",
            json=payload,
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            print(f"   [OK] Correctly rejected invalid token!")
            print(f"   Detail: {result['detail']}")
            return True
        else:
            print(f"   [ERROR] Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] {str(e)}")
        return False


if __name__ == "__main__":
    print("\n[START] Email Verification Testing Suite")
    print("This tests the Item 8 implementation\n")
    
    # Run tests
    test1_passed = test_email_verification()
    test2_passed = test_invalid_token()
    
    # Summary
    print("\n" + "="*60)
    print("[SUMMARY] TEST RESULTS")
    print("="*60)
    print(f"Email Verification: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Invalid Token Rejection: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n[COMPLETE] ALL TESTS PASSED! Item 8 is complete.")
    else:
        print("\n[INCOMPLETE] Some tests failed. Review the output above.")
