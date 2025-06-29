#!/usr/bin/env python3
"""
Test API endpoints directly.
"""

import requests
import json

def test_api():
    base_url = "http://localhost:5000"
    
    print("Testing API endpoints...")
    
    try:
        # Test the overview endpoint
        response = requests.get(f"{base_url}/api/lead_traders_overview/1")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"JSON Data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.status_code}")
            
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_api()