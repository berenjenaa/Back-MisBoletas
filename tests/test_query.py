#!/usr/bin/env python
"""Test direct Supabase query to verify service_role_key works with RLS enabled"""

from app.core.config import supabase
import json

print("Testing Supabase connection with service_role_key and RLS enabled...")
print()

# Test 1: Query categorias table
try:
    print("1. Querying categorias table...")
    response = supabase.table("categorias").select("*").limit(1).execute()
    print(f"   ✓ Query successful!")
    print(f"   Data count: {len(response.data)}")
    if response.data:
        print(f"   First record: {json.dumps(response.data[0], indent=6, default=str)}")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}")
    print(f"   Message: {str(e)}")

print()

# Test 2: Check perfiles table  
try:
    print("2. Querying perfiles table...")
    response = supabase.table("perfiles").select("*").limit(1).execute()
    print(f"   ✓ Query successful!")
    print(f"   Data count: {len(response.data)}")
    if response.data:
        print(f"   First record: {json.dumps(response.data[0], indent=6, default=str)}")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}")
    print(f"   Message: {str(e)}")

print()

# Test 3: Check productos table
try:
    print("3. Querying productos table...")
    response = supabase.table("productos").select("*").limit(1).execute()
    print(f"   ✓ Query successful!")
    print(f"   Data count: {len(response.data)}")
    if response.data:
        print(f"   First record: {json.dumps(response.data[0], indent=6, default=str)}")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}")
    print(f"   Message: {str(e)}")
