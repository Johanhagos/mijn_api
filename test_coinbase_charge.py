#!/usr/bin/env python3
"""
Test script for Coinbase Commerce charge creation.
Tests the /api/coinbase/create-charge endpoint.
"""
import requests
import json

# Configuration
API_URL = "https://api.apiblockchain.io/api/coinbase/create-charge"
# API_URL = "http://127.0.0.1:8000/api/coinbase/create-charge"  # For local testing

def test_create_charge():
    """Test creating a Coinbase Commerce charge"""
    
    # Test data
    payload = {
        "session_id": f"test_sess_{int(requests.utils.default_headers()['User-Agent'].split('/')[-1].replace('.', ''))}",
        "amount": 20.00,
        "currency": "EUR",
        "name": "Starter Plan - API Blockchain",
        "description": "Monthly subscription to Starter plan"
    }
    
    print("Testing Coinbase Commerce charge creation...")
    print(f"API URL: {API_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nSending request...\n")
    
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("\nResponse Body:")
        
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
            
            if response.status_code == 200 and data.get('success'):
                print("\n✅ SUCCESS!")
                print(f"Charge ID: {data.get('charge_id')}")
                print(f"Hosted URL: {data.get('hosted_url')}")
                print(f"Expires At: {data.get('expires_at')}")
                print("\nYou can now test the payment by opening the hosted URL in your browser.")
                return True
            else:
                print(f"\n❌ FAILED: {data.get('error', 'Unknown error')}")
                return False
                
        except json.JSONDecodeError:
            print(response.text)
            print("\n❌ FAILED: Invalid JSON response")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST FAILED: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    test_create_charge()
