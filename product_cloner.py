#!/usr/bin/env python3
"""
SAP Product Clone Automation Tool
Reads existing product -> transforms -> creates new product
"""

import json
import sys
import os
import argparse
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
import logging
import io
from urllib.parse import quote

# Configure logging (file in UTF-8, stream wrapped to avoid encoding errors)
file_handler = logging.FileHandler('product_cloner.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Wrap stderr buffer with a TextIOWrapper that replaces unencodable characters
stream_wrapper = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
stream_handler = logging.StreamHandler(stream_wrapper)
stream_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
logger = logging.getLogger(__name__)

DEFAULT_ORG_TRANSFORMS = {
    'to_Plant': {
        'Plant': '1710',
        'ProcurementType': 'E'
    },
    'to_SalesDelivery': {
        'ProductSalesOrg': '1710',
        'ProductDistributionChnl': '10'
    },
    'to_ProductSalesTax': {
        'Country': 'US',
        'TaxCategory': 'UTXJ',
        'TaxClassification': '1'
    },
    'to_Valuation': {
        'ValuationArea': '1710',
        'PriceDeterminationControl': '2'
    }
}

DEFAULT_SUPPLY_PLANNING = {
    'Plant': '1710',
    'ProcurementType': 'E',
    'MRPType': 'PD',
    'MRPResponsible': '001',
    'LotSizingProcedure': 'EX'
}

DEFAULT_STORAGE_LOCATION = {
    'Plant': '1710',
    'StorageLocation': '171A'
}


class ProductCloner:
    """Main class for reading, transforming, and creating SAP products"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config = self._load_config(config_file)
        self.logger = logger
        self._configure_ssl_warnings()
        
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

    def _configure_ssl_warnings(self) -> None:
        """Hide urllib3 warnings when SSL verification is intentionally disabled."""
        if not self.config.get('verify_ssl', False):
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    
    def read_from_file(self, file_path: str) -> Dict[str, Any]:
        """Read product data from local JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            product = data.get('d', data)
            self.logger.info(f"Loaded product from {file_path}")
            return product
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            raise
    
    def read_from_sap_api(self, product_id: str, expand: bool = True) -> Dict[str, Any]:
        """Fetch product from SAP API"""
        if not self.config.get('username'):
            self.logger.error("SAP credentials not configured. Use config.json")
            raise ValueError("Missing SAP credentials")
        
        encoded_product_id = quote(product_id, safe="")
        url = (f"{self.config['sap_base_url']}{self.config['sap_api_path']}"
               f"/A_Product('{encoded_product_id}')")

        params = {"$format": "json"}
        if expand:
            params["$expand"] = (
                "to_Plant,to_SalesDelivery,to_ProductSalesTax,"
                "to_Valuation,to_ProductUnitsOfMeasure"
            )

        headers = {
            "Accept": "application/json",
        }
        
        try:
            auth = HTTPBasicAuth(self.config['username'], self.config['password'])
            response = requests.get(
                url,
                auth=auth,
                verify=self.config.get('verify_ssl', False),
                params=params,
                headers=headers
            )
            response.raise_for_status()

            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as e:
                # Log response snippet when JSON parsing fails
                snippet = response.text[:200]
                self.logger.error(
                    f"Failed to parse JSON from SAP (status={response.status_code}). Response snippet: {snippet!r}"
                )
                raise ValueError(
                    "SAP returned a non-JSON response. Check that the service supports JSON "
                    "or open the logged response snippet for details."
                ) from e

            product = data.get('d', {})
            self.logger.info(f"Fetched product {product_id} from SAP API")
            return product
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch from SAP: {e}")
            raise
    
    def transform_product(self, product: Dict[str, Any], 
                         transforms: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformations to product data"""
        cloned = self._deep_copy_structure(product)

        for field in transforms.get('remove_fields', []):
            if field in cloned:
                old_value = cloned.pop(field)
                self.logger.info(f"  {field}: removed old value '{old_value}'")

        description = transforms.get('product_description')
        if description:
            cloned['to_Description'] = {
                'results': [
                    {
                        'Language': transforms.get('description_language', 'EN'),
                        'ProductDescription': description[:40]
                    }
                ]
            }
            self.logger.info(f"  to_Description.ProductDescription: -> '{description[:40]}'")

        for field, new_value in transforms.get('fields', {}).items():
            if field in cloned:
                old_value = cloned[field]
                cloned[field] = new_value
                self.logger.info(f"  {field}: '{old_value}' -> '{new_value}'")
            else:
                cloned[field] = new_value
                self.logger.info(f"  {field}: added '{new_value}'")
        
        for nav_property, nested_fields in transforms.get('nested', {}).items():
            if nav_property not in cloned or 'results' not in cloned.get(nav_property, {}):
                cloned[nav_property] = {'results': [{}]}

            results = cloned.get(nav_property, {}).get('results', [])
            for item in results:
                for field, new_value in nested_fields.items():
                    item[field] = new_value
                    self.logger.info(f"  {nav_property}.{field}: -> '{new_value}'")

        supply_planning = transforms.get('supply_planning')
        storage_location = transforms.get('storage_location')
        if supply_planning or storage_location:
            if 'to_Plant' not in cloned or 'results' not in cloned.get('to_Plant', {}):
                cloned['to_Plant'] = {'results': [{}]}

            for plant in cloned.get('to_Plant', {}).get('results', []):
                if supply_planning:
                    plant['to_ProductSupplyPlanning'] = self._deep_copy_structure(supply_planning)
                    self.logger.info(
                        f"  to_Plant.to_ProductSupplyPlanning.LotSizingProcedure: -> "
                        f"'{supply_planning.get('LotSizingProcedure')}'"
                    )

                if storage_location:
                    plant['to_StorageLocation'] = {
                        'results': [self._deep_copy_structure(storage_location)]
                    }
                    self.logger.info(
                        f"  to_Plant.to_StorageLocation.StorageLocation: -> "
                        f"'{storage_location.get('StorageLocation')}'"
                    )
        
        self.logger.info(f"Product transformed successfully")
        return cloned
    
    def validate_payload(self, product: Dict[str, Any]) -> bool:
        """Validate that product has required fields"""
        required_fields = [
            'ProductType',
            'BaseUnit',
            'to_Plant',
            'to_ProductUnitsOfMeasure',
            'to_SalesDelivery',
            'to_Valuation'
        ]
        
        missing = [f for f in required_fields if f not in product or not product[f]]
        
        if missing:
            self.logger.error(f"Validation failed. Missing: {missing}")
            return False
        
        self.logger.info(f"Payload validation passed")
        return True
    
    def post_to_sap(self, product: Dict[str, Any], dry_run: bool = True) -> Optional[str]:
        """POST product to SAP to create new material"""
        if not self.config.get('username'):
            self.logger.error("SAP credentials not configured")
            return None
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No actual POST will be sent")
            return None
        
        url = (f"{self.config['sap_base_url']}{self.config['sap_api_path']}/A_Product")
        payload = self._prepare_post_payload(product)
        self._save_debug_payload(payload)
        
        try:
            session = requests.Session()
            auth = HTTPBasicAuth(self.config['username'], self.config['password'])
            csrf_token = self._fetch_csrf_token(session, auth, url)

            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrf_token
            }

            response = session.post(
                url,
                json=payload,
                auth=auth,
                verify=self.config.get('verify_ssl', False),
                headers=headers
            )
            if response.status_code >= 400:
                snippet = response.text[:1000]
                self.logger.error(
                    f"SAP rejected POST with status={response.status_code}. Response snippet: {snippet!r}"
                )
            response.raise_for_status()

            try:
                resp_data = response.json()
            except ValueError:
                snippet = response.text[:200]
                self.logger.error(
                    f"Failed to parse JSON response after POST (status={response.status_code}). Snippet: {snippet!r}"
                )
                raise

            new_product_id = resp_data.get('d', {}).get('Product')
            self.logger.info(f"Product created successfully: {new_product_id}")
            return new_product_id
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to POST to SAP: {e}")
            raise

    def _fetch_csrf_token(self, session: requests.Session, auth: HTTPBasicAuth, url: str) -> str:
        """Fetch an SAP Gateway CSRF token and keep cookies in the session."""
        response = session.get(
            url,
            auth=auth,
            verify=self.config.get('verify_ssl', False),
            headers={
                'Accept': 'application/json',
                'X-CSRF-Token': 'Fetch'
            },
            params={'$format': 'json'}
        )
        response.raise_for_status()

        token = response.headers.get('X-CSRF-Token') or response.headers.get('x-csrf-token')
        if not token:
            snippet = response.text[:300]
            self.logger.error(f"SAP did not return an X-CSRF-Token header. Response snippet: {snippet!r}")
            raise ValueError("SAP did not return an X-CSRF-Token header")

        self.logger.info("Fetched SAP CSRF token")
        return token
    
    def _deep_copy_structure(self, obj: Any) -> Any:
        """Deep copy a product object maintaining structure"""
        if isinstance(obj, dict):
            return {k: self._deep_copy_structure(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy_structure(item) for item in obj]
        else:
            return obj
    
    def _prepare_post_payload(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare product data for POST while letting SAP assign Product."""
        return self._clean_for_post(product)

    def _clean_for_post(self, value: Any) -> Any:
        """Remove OData metadata and source product IDs from a payload tree."""
        if isinstance(value, dict):
            if set(value.keys()) == {'__deferred'}:
                return None

            cleaned = {}
            for key, nested_value in value.items():
                if key == '__metadata' or key == 'Product':
                    continue
                cleaned_value = self._clean_for_post(nested_value)
                if cleaned_value is not None:
                    cleaned[key] = cleaned_value
            return cleaned

        if isinstance(value, list):
            return [
                cleaned_item
                for item in value
                if (cleaned_item := self._clean_for_post(item)) is not None
            ]

        return value

    def _save_debug_payload(self, payload: Dict[str, Any]) -> None:
        """Save the latest POST payload for SAP error troubleshooting."""
        debug_file = 'last_post_payload.json'
        try:
            with open(debug_file, 'w') as f:
                json.dump(payload, f, indent=2)
            self.logger.info(f"Saved POST payload debug copy to {debug_file}")
        except OSError as e:
            self.logger.warning(f"Could not save POST payload debug copy: {e}")


def _first_nested_value(product: Dict[str, Any], nav_property: str, field: str) -> Any:
    """Return the first value from an expanded OData navigation collection."""
    results = product.get(nav_property, {}).get('results', [])
    if not results:
        return None
    return results[0].get(field)


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
        try:
            product = cloner.read_from_sap_api(product_id)
        except Exception as e:
            print(f"Failed to fetch product from SAP: {e}")
            return
    else:
        print("Invalid choice")
        return
    
    print(f"\nSource Product: {product.get('Product', 'N/A')}")
    
    print("\n[Step 2] Define Transformations")
    print("New Product ID: SAP will assign automatically")
    new_description = input("New Description: ").strip()
    standard_price = input("Standard Price (leave blank to copy source): ").strip()

    nested_transforms = cloner._deep_copy_structure(DEFAULT_ORG_TRANSFORMS)
    
    transforms = {
        'remove_fields': ['Product'],
        'product_description': new_description,
        'supply_planning': DEFAULT_SUPPLY_PLANNING,
        'storage_location': DEFAULT_STORAGE_LOCATION,
        'fields': {
            'ProductOldID': '',
            'Division': '00'
        },
        'nested': nested_transforms
    }
    
    if standard_price:
        transforms['nested'].setdefault('to_Valuation', {})['StandardPrice'] = standard_price

    print("\n[Step 3] Applying Transformations...")
    transformed = cloner.transform_product(product, transforms)
    
    print("\n[Step 4] Validating Payload...")
    if not cloner.validate_payload(transformed):
        print("Validation failed. Aborting.")
        return
    
    print("\n[Step 5] Preview Transformed Product")
    print(json.dumps({
        'Product': 'SAP generated',
        'ProductType': transformed.get('ProductType'),
        'BaseUnit': transformed.get('BaseUnit'),
        'CreationDate': transformed.get('CreationDate'),
        'Plant': _first_nested_value(transformed, 'to_Plant', 'Plant'),
        'SalesOrg': _first_nested_value(transformed, 'to_SalesDelivery', 'ProductSalesOrg'),
        'DistributionChannel': _first_nested_value(transformed, 'to_SalesDelivery', 'ProductDistributionChnl'),
        'Division': transformed.get('Division'),
        'TaxClassification': _first_nested_value(transformed, 'to_ProductSalesTax', 'TaxClassification'),
        'ValuationArea': _first_nested_value(transformed, 'to_Valuation', 'ValuationArea'),
        'StandardPrice': _first_nested_value(transformed, 'to_Valuation', 'StandardPrice')
    }, indent=2))
    
    print("\n[Step 6] Save & Publish")
    save_choice = input("Save transformed product to file? (y/n): ").strip().lower()
    
    if save_choice == 'y':
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"product_sap_generated_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump({'d': transformed}, f, indent=2)
        print(f"Saved to {output_file}")
    
    post_choice = input("POST to SAP? (y/n): ").strip().lower()
    
    if post_choice == 'y':
        dry_run = input("Dry run only? (y/n): ").strip().lower() == 'y'
        try:
            cloner.post_to_sap(transformed, dry_run=dry_run)
            if not dry_run:
                print(f"Product created successfully!")
        except Exception as e:
            print(f"Post failed: {e}")


def batch_mode(source_file: str, config_file: str, dry_run: bool = True):
    """Batch mode for automated processing"""
    cloner = ProductCloner(config_file)
    
    print(f"Processing {source_file}...")
    product = cloner.read_from_file(source_file)
    
    transforms = {
        'remove_fields': ['Product'],
        'supply_planning': DEFAULT_SUPPLY_PLANNING,
        'storage_location': DEFAULT_STORAGE_LOCATION,
        'fields': {
            'ProductOldID': '',
            'Division': '00'
        },
        'nested': DEFAULT_ORG_TRANSFORMS
    }
    
    transformed = cloner.transform_product(product, transforms)
    
    if cloner.validate_payload(transformed):
        result = cloner.post_to_sap(transformed, dry_run=dry_run)
        print(f"Batch processing complete")
    else:
        print(f"Batch processing failed validation")


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
