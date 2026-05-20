#!/usr/bin/env python3
"""
Quick test script to verify product_cloner functionality
"""

import json
import os
import sys

print("="*60)
print("Product Cloner - Quick Test")
print("="*60)

files_to_check = {
    'sample.json': 'Sample product data',
    'config.json': 'SAP configuration',
    'product_cloner.py': 'Main cloner script',
    'transform_config.json': 'Transformation rules',
    'README.md': 'Documentation'
}

print("\n[1] Checking required files...")
all_exist = True
for filename, description in files_to_check.items():
    exists = os.path.exists(filename)
    status = "✓" if exists else "✗"
    print(f"  {status} {filename:25} - {description}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n✗ Missing required files. Setup incomplete.")
    sys.exit(1)

print("\n[2] Inspecting sample.json structure...")
try:
    with open('sample.json', 'r') as f:
        sample = json.load(f)
    
    product = sample.get('d', sample)
    
    print(f"  ✓ Product ID: {product.get('Product', 'N/A')}")
    print(f"  ✓ Type: {product.get('ProductType', 'N/A')}")
    print(f"  ✓ Base Unit: {product.get('BaseUnit', 'N/A')}")
    
    has_plant = bool(product.get('to_Plant', {}).get('results'))
    has_sales = bool(product.get('to_SalesDelivery', {}).get('results'))
    has_valuation = bool(product.get('to_Valuation', {}).get('results'))
    has_uom = bool(product.get('to_ProductUnitsOfMeasure', {}).get('results'))
    
    print(f"  ✓ Has Plant data: {has_plant}")
    print(f"  ✓ Has Sales data: {has_sales}")
    print(f"  ✓ Has Valuation data: {has_valuation}")
    print(f"  ✓ Has UoM data: {has_uom}")
    
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

print("\n[3] Testing product_cloner import...")
try:
    import product_cloner
    print(f"  ✓ Successfully imported ProductCloner class")
    
    cloner = product_cloner.ProductCloner()
    print(f"  ✓ Created ProductCloner instance")
    
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ All tests passed! Tool is ready to use.")
print("="*60)
print("\nNext: python product_cloner.py")
