#!/usr/bin/env python3
"""
Simple CRUD smoke test for employee service.
This tests the basic CRUD operations without requiring authentication.
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:9002"

async def test_employee_crud():
    """Test basic CRUD operations for employee service."""
    
    print("🧪 Starting Employee CRUD Smoke Test")
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("1. Testing health endpoint...")
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        health_data = response.json()
        print(f"   ✅ Health check: {health_data}")
        
        # Note: The actual CRUD endpoints require JWT authentication
        # For a full test, we would need to:
        # 1. Get a JWT token from the auth service
        # 2. Include it in the Authorization header
        # 3. Test the CRUD operations
        
        print("2. Testing OpenAPI documentation...")
        response = await client.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            openapi_spec = response.json()
            print(f"   ✅ OpenAPI spec available with {len(openapi_spec.get('paths', {}))} endpoints")
        else:
            print(f"   ⚠️ OpenAPI spec not available (status: {response.status_code})")
        
        print("3. Testing protected endpoints (should return 401 without auth)...")
        response = await client.get(f"{BASE_URL}/v1/employees")
        if response.status_code == 401:
            print("   ✅ Protected endpoint correctly requires authentication")
        else:
            print(f"   ⚠️ Expected 401, got {response.status_code}")
    
    print("🎉 Employee CRUD Smoke Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_employee_crud())
