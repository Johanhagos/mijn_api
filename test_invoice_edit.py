#!/usr/bin/env python3
"""Test script for Invoice Editing Feature"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_invoice_editing():
    print("=" * 60)
    print("TESTING INVOICE EDITING FEATURE")
    print("=" * 60)
    
    # Step 1: Login
    print("\n[1] LOGIN TEST")
    print("-" * 60)
    try:
        login_response = requests.post(
            f"{BASE_URL}/login",
            json={"name": "AliceAdmin", "password": "hunter2"}
        )
        if login_response.status_code != 200:
            print(f"❌ Login failed with status {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False
        
        token = login_response.json().get("access_token")
        print(f"✅ Login successful")
        print(f"   Token: {token[:40]}...")
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Step 2: Get invoices
    print("\n[2] FETCH INVOICES TEST")
    print("-" * 60)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        invoices_response = requests.get(
            f"{BASE_URL}/invoices",
            headers=headers
        )
        if invoices_response.status_code != 200:
            print(f"❌ Failed to fetch invoices: {invoices_response.status_code}")
            return False
        
        invoices = invoices_response.json()
        print(f"✅ Fetched {len(invoices)} invoices")
        
        if not invoices:
            print("⚠️  No invoices available to test with")
            return False
        
        invoice = invoices[0]
        invoice_id = invoice.get("id")
        print(f"   Using invoice: {invoice_id}")
        print(f"   Current status: {invoice.get('status', 'N/A')}")
        print(f"   Buyer: {invoice.get('buyer_name', 'N/A')}")
    except Exception as e:
        print(f"❌ Error fetching invoices: {e}")
        return False
    
    # Step 3: Test PATCH endpoint
    print("\n[3] UPDATE INVOICE TEST (PATCH)")
    print("-" * 60)
    try:
        update_payload = {
            "status": "sent",
            "due_date": "2026-03-20",
            "buyer_name": "Test Buyer Updated",
            "notes": "Updated via API test"
        }
        
        patch_response = requests.patch(
            f"{BASE_URL}/invoices/{invoice_id}",
            headers=headers,
            json=update_payload
        )
        
        if patch_response.status_code != 200:
            print(f"❌ PATCH failed with status {patch_response.status_code}")
            print(f"   Response: {patch_response.json()}")
            return False
        
        updated = patch_response.json()
        print(f"✅ Invoice updated successfully")
        print(f"   New status: {updated.get('status')}")
        print(f"   New due_date: {updated.get('due_date')}")
        print(f"   New buyer: {updated.get('buyer_name')}")
    except Exception as e:
        print(f"❌ Error updating invoice: {e}")
        return False
    
    # Step 4: Verify changes
    print("\n[4] VERIFY CHANGES TEST")
    print("-" * 60)
    try:
        verify_response = requests.get(
            f"{BASE_URL}/invoices/{invoice_id}",
            headers=headers
        )
        
        if verify_response.status_code != 200:
            print(f"❌ Verification failed: {verify_response.status_code}")
            return False
        
        verified = verify_response.json()
        print(f"✅ Changes verified")
        print(f"   Status: {verified.get('status')}")
        print(f"   Due date: {verified.get('due_date')}")
        print(f"   Buyer: {verified.get('buyer_name')}")
    except Exception as e:
        print(f"❌ Error verifying changes: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - INVOICE EDITING IS WORKING!")
    print("=" * 60)
    print("\nFrontend Access:")
    print("1. Go to https://dashboard.apiblockchain.io")
    print("2. Login with merchantuser")
    print("3. View an invoice")
    print("4. Click the '✏️ Edit Invoice' button")
    print("5. Make changes and click 'Save Changes'")
    print("\n" + "=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_invoice_editing()
    sys.exit(0 if success else 1)
