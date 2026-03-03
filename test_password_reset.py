"""
Test script for password reset endpoint (Item 9)
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
from auth import verify_password, hash_password

BASE_URL = "http://localhost:5000"

def test_password_reset_flow():
    """Test the complete password reset flow"""
    
    print("\n" + "="*60)
    print("[TEST] Testing Password Reset Flow (Item 9)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 1. Get demo user
        print("\n[STEP 1] Getting demo user...")
        demo_user = db.query(User).filter(User.email == "admin@demo.example.com").first()
        
        if not demo_user:
            print("[ERROR] Demo user not found")
            return False
        
        original_hash = demo_user.password_hash
        print(f"   [OK] Found user: {demo_user.email}")
        
        # 2. Request password reset
        print("\n[STEP 2] Requesting password reset...")
        response = requests.post(
            f"{BASE_URL}/auth/password-reset/request",
            json={"email": demo_user.email},
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Reset requested")
            print(f"   Message: {result['message']}")
            
            # Extract token (in production, this would be from email)
            if "token" in result:
                reset_token = result["token"]
                print(f"   Token: {reset_token[:20]}... (truncated)")
            else:
                print("[ERROR] No token returned")
                return False
        else:
            print(f"   [ERROR] Failed to request reset")
            print(f"   Response: {response.text}")
            return False
        
        # 3. Confirm password reset
        print("\n[STEP 3] Confirming password reset with new password...")
        
        new_password = "NewPassword123!"
        reset_payload = {
            "token": reset_token,
            "new_password": new_password
        }
        
        response = requests.post(
            f"{BASE_URL}/auth/password-reset/confirm",
            json=reset_payload,
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Password reset confirmed!")
            print(f"   Message: {result['message']}")
            print(f"   Email: {result['email']}")
            
            # 4. Verify in database and test new password
            print("\n[STEP 4] Verifying password change...")
            db.refresh(demo_user)
            
            if demo_user.password_reset_token is None:
                print("   [OK] Reset token cleared")
            else:
                print("   [WARN] Reset token not cleared")
            
            if demo_user.password_hash != original_hash:
                print("   [OK] Password hash changed")
            else:
                print("   [ERROR] Password hash unchanged")
                return False
            
            # Verify new password works
            if verify_password(new_password, demo_user.password_hash):
                print("   [OK] New password is correct")
            else:
                print("   [ERROR] New password verification failed")
                return False
            
            print("\n[SUCCESS] PASSWORD RESET FLOW COMPLETED!")
            
            # Reset password back to original for other tests
            print("\n[CLEANUP] Restoring original password...")
            demo_user.password_hash = hash_password("admin123")
            db.commit()
            print("   [OK] Original password restored")
            
            return True
        else:
            print(f"   [ERROR] Failed to confirm reset")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_invalid_reset_token():
    """Test rejection of invalid reset tokens"""
    
    print("\n" + "="*60)
    print("[TEST] Testing Invalid Reset Token Rejection")
    print("="*60)
    
    try:
        print("\n[STEP 1] Attempting reset with invalid token...")
        
        payload = {
            "token": "invalid-reset-token",
            "new_password": "SomeNewPassword123!"
        }
        
        response = requests.post(
            f"{BASE_URL}/auth/password-reset/confirm",
            json=payload,
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            print(f"   [OK] Correctly rejected invalid token")
            print(f"   Detail: {result['detail']}")
            return True
        else:
            print(f"   [ERROR] Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] {str(e)}")
        return False


def test_nonexistent_email():
    """Test password reset for non-existent email"""
    
    print("\n" + "="*60)
    print("[TEST] Testing Non-Existent Email Handling")
    print("="*60)
    
    try:
        print("\n[STEP 1] Requesting reset for non-existent email...")
        
        response = requests.post(
            f"{BASE_URL}/auth/password-reset/request",
            json={"email": "nonexistent@example.com"},
            timeout=10
        )
        
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Gracefully handled non-existent email")
            print(f"   Message: {result['message']}")
            # Should NOT return a token for security
            if "token" not in result or result.get("token") is None:
                print("   [OK] No token exposed (good security)")
                return True
            else:
                print("   [WARN] Token returned for non-existent email (security risk)")
                return False
        else:
            print(f"   [ERROR] Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] {str(e)}")
        return False


if __name__ == "__main__":
    print("\n[START] Password Reset Testing Suite")
    print("This tests the Item 9 implementation\n")
    
    # Run tests
    test1_passed = test_password_reset_flow()
    test2_passed = test_invalid_reset_token()
    test3_passed = test_nonexistent_email()
    
    # Summary
    print("\n" + "="*60)
    print("[SUMMARY] TEST RESULTS")
    print("="*60)
    print(f"Password Reset Flow: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Invalid Token Rejection: {'PASSED' if test2_passed else 'FAILED'}")
    print(f"Non-Existent Email Handling: {'PASSED' if test3_passed else 'FAILED'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n[COMPLETE] ALL TESTS PASSED! Item 9 is complete.")
    else:
        print("\n[INCOMPLETE] Some tests failed. Review the output above.")
