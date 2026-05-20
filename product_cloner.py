#!/usr/bin/env python3
"""
SAP Product Clone Automation Tool
Reads existing product → transforms → creates new product
"""

import json
import sys
import os
import argparse
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('product_cloner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProductCloner:
    """Main class for reading, transforming, and creating SAP products"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config = self._load_config(config_file)
        self.logger = logger
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not os.path.exists(config_file):
            self.logger.warning(f"Config file {config_file} not found. Using defaults.")
            return {
                "sap_base_url": "https://CLOUD9.WAY2ERP.US:44300",
                "sap_api_path": "/sap/opu/odata/sap/API_PRODUCT_SRV",
                "username": "",
                "password": "",
                "dry_run": True,
                "verify_ssl": False
            }
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def read_from_file(self, file_path: str) -> Dict[str, Any]:
        """Read product data from local JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            product = data.get('d', data)
            self.logger.info(f"✓ Loaded product from {file_path}")
            return product
        except Exception as e:
            self.logger.error(f"✗ Failed to read {file_path}: {e}")
            raise
    
    def read_from_sap_api(self, product_id: str, expand: bool = True) -> Dict[str, Any]:
        """Fetch product from SAP API"""
        if not self.config.get('username'):
            self.logger.error("SAP credentials not configured. Use config.json")
            raise ValueError("Missing SAP credentials")
        
        url = (f"{self.config['sap_base_url']}{self.config['sap_api_path']}"
               f"/A_Product('{product_id}')")
        
        if expand:
            url += "?$expand=to_Plant,to_SalesDelivery,to_Valuation,to_ProductUnitsOfMeasure"
        
        try:
            auth = HTTPBasicAuth(self.config['username'], self.config['password'])
            response = requests.get(
                url,
                auth=auth,
                verify=self.config.get('verify_ssl', False)
            )
            response.raise_for_status()
            
            product = response.json().get('d', {})
            self.logger.info(f"✓ Fetched product {product_id} from SAP API")
            return product
        except Exception as e:
            self.logger.error(f"✗ Failed to fetch from SAP: {e}")
            raise
    
    def transform_product(self, product: Dict[str, Any], 
                         transforms: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformations to product data"""
        cloned = self._deep_copy_structure(product)
        
        for field, new_value in transforms.get('fields', {}).items():
            if field in cloned:
                old_value = cloned[field]
                cloned[field] = new_value
                self.logger.info(f"  {field}: '{old_value}' → '{new_value}'")
        
        if 'to_Plant' in cloned and 'to_Plant' in transforms.get('nested', {}):
            for plant in cloned.get('to_Plant', {}).get('results', []):
                for field, new_value in transforms['nested']['to_Plant'].items():
                    plant[field] = new_value
                    self.logger.info(f"  Plant.{field}: → '{new_value}'")
        
        self.logger.info(f"✓ Product transformed successfully")
        return cloned
    
    def validate_payload(self, product: Dict[str, Any]) -> bool:
        """Validate that product has required fields"""
        required_fields = [
            'Product',
            'ProductType',
            'BaseUnit',
            'to_Plant',
            'to_ProductUnitsOfMeasure',
            'to_SalesDelivery',
            'to_Valuation'
        ]
        
        missing = [f for f in required_fields if f not in product or not product[f]]
        
        if missing:
            self.logger.error(f"✗ Validation failed. Missing: {missing}")
            return False
        
        self.logger.info(f"✓ Payload validation passed")
        return True
    
    def post_to_sap(self, product: Dict[str, Any], dry_run: bool = True) -> Optional[str]:
        """POST product to SAP to create new material"""
        if not self.config.get('username'):
            self.logger.error("SAP credentials not configured")
            return None
        
        if dry_run:
            self.logger.info("🔧 DRY RUN MODE - No actual POST will be sent")
            return None
        
        url = (f"{self.config['sap_base_url']}{self.config['sap_api_path']}/A_Product")
        
        payload = self._prepare_post_payload(product)
        
        try:
            auth = HTTPBasicAuth(self.config['username'], self.config['password'])
            response = requests.post(
                url,
                json=payload,
                auth=auth,
                verify=self.config.get('verify_ssl', False),
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            
            new_product_id = response.json().get('d', {}).get('Product')
            self.logger.info(f"✓ Product created successfully: {new_product_id}")
            return new_product_id
        except Exception as e:
            self.logger.error(f"✗ Failed to POST to SAP: {e}")
            raise
    
    def _deep_copy_structure(self, obj: Any) -> Any:
        """Deep copy a product object maintaining structure"""
        if isinstance(obj, dict):
            return {k: self._deep_copy_structure(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy_structure(item) for item in obj]
        else:
            return obj
    
    def _prepare_post_payload(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare product data for POST (remove metadata, flatten navigation properties)"""
        payload = {}
        
        for key, value in product.items():
            if not key.startswith('__') and not key.startswith('to_'):
                if key not in ['to_Description', 'to_ProductBasicText', 'to_ProductInspectionText',
                              'to_ProductProcurement', 'to_ProductPurchaseText', 'to_ProductQualityMgmt',
                              'to_ProductSales', 'to_ProductSalesTax', 'to_ProductStorage']:
                    payload[key] = value
        
        return payload


def interactive_mode():
    """Interactive CLI for product cloning"""
    print("\n" + "="*60)
    print("SAP Product Clone Automation Tool")
    print("="*60)
    
    cloner = ProductCloner()
    
    print("\n[Step 1] Read Source Product")
    print("1. Load from local file")
    print("2. Fetch from SAP API")
    source_choice = input("\nSelect option (1-2): ").strip()
    
    if source_choice == '1':
        file_path = input("Enter JSON file path: ").strip()
        product = cloner.read_from_file(file_path)
    elif source_choice == '2':
        product_id = input("Enter SAP Product ID: ").strip()
        product = cloner.read_from_sap_api(product_id)
    else:
        print("Invalid choice")
        return
    
    print(f"\nSource Product: {product.get('Product', 'N/A')}")
    
    print("\n[Step 2] Define Transformations")
    new_product_id = input("New Product ID: ").strip()
    new_description = input("New Description: ").strip()
    new_gtin = input("New GTIN (leave blank to skip): ").strip()
    
    transforms = {
        'fields': {
            'Product': new_product_id,
            'ProductOldID': ''
        },
        'nested': {}
    }
    
    if new_gtin:
        transforms['fields']['GlobalTradeItemNumber'] = new_gtin
    
    print("\n[Step 3] Applying Transformations...")
    transformed = cloner.transform_product(product, transforms)
    
    print("\n[Step 4] Validating Payload...")
    if not cloner.validate_payload(transformed):
        print("✗ Validation failed. Aborting.")
        return
    
    print("\n[Step 5] Preview Transformed Product")
    print(json.dumps({
        'Product': transformed.get('Product'),
        'ProductType': transformed.get('ProductType'),
        'BaseUnit': transformed.get('BaseUnit'),
        'CreationDate': transformed.get('CreationDate'),
        'to_Plant': len(transformed.get('to_Plant', {}).get('results', [])),
        'to_SalesDelivery': len(transformed.get('to_SalesDelivery', {}).get('results', [])),
        'to_Valuation': len(transformed.get('to_Valuation', {}).get('results', []))
    }, indent=2))
    
    print("\n[Step 6] Save & Publish")
    save_choice = input("Save transformed product to file? (y/n): ").strip().lower()
    
    if save_choice == 'y':
        output_file = f"product_{new_product_id}_transformed.json"
        with open(output_file, 'w') as f:
            json.dump({'d': transformed}, f, indent=2)
        print(f"✓ Saved to {output_file}")
    
    post_choice = input("POST to SAP? (y/n): ").strip().lower()
    
    if post_choice == 'y':
        dry_run = input("Dry run only? (y/n): ").strip().lower() == 'y'
        try:
            cloner.post_to_sap(transformed, dry_run=dry_run)
            if not dry_run:
                print(f"✓ Product created successfully!")
        except Exception as e:
            print(f"✗ Post failed: {e}")


def batch_mode(source_file: str, config_file: str, dry_run: bool = True):
    """Batch mode for automated processing"""
    cloner = ProductCloner(config_file)
    
    print(f"Processing {source_file}...")
    product = cloner.read_from_file(source_file)
    
    transforms = {
        'fields': {
            'Product': '500',
            'ProductOldID': ''
        },
        'nested': {}
    }
    
    transformed = cloner.transform_product(product, transforms)
    
    if cloner.validate_payload(transformed):
        result = cloner.post_to_sap(transformed, dry_run=dry_run)
        print(f"✓ Batch processing complete")
    else:
        print(f"✗ Batch processing failed validation")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SAP Product Clone Automation')
    parser.add_argument('--batch', type=str, help='Batch mode: input file path')
    parser.add_argument('--config', type=str, default='config.json', help='Config file')
    parser.add_argument('--no-dry-run', action='store_true', help='Actually POST to SAP')
    
    args = parser.parse_args()
    
    if args.batch:
        batch_mode(args.batch, args.config, dry_run=not args.no_dry_run)
    else:
        interactive_mode()