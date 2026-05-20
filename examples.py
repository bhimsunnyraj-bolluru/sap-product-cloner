#!/usr/bin/env python3
"""
Example usage of ProductCloner as a library.
"""

import json

from product_cloner import ProductCloner


def example_1_simple_file_clone():
    """Example 1: Simple clone from file."""
    print("\n" + "=" * 60)
    print("Example 1: Simple File Clone")
    print("=" * 60)

    cloner = ProductCloner("config.json")
    product = cloner.read_from_file("sample.json")
    print(f"Source: Product {product['Product']}")

    transforms = {"remove_fields": ["Product"], "fields": {}, "nested": {}}
    cloned = cloner.transform_product(product, transforms)

    if cloner.validate_payload(cloned):
        print("OK Target: Product will be assigned by SAP")


def example_2_bulk_transformation():
    """Example 2: Bulk transformation with config."""
    print("\n" + "=" * 60)
    print("Example 2: Bulk Transformation")
    print("=" * 60)

    cloner = ProductCloner("config.json")
    product = cloner.read_from_file("sample.json")

    with open("transform_config.json", "r") as f:
        transform_spec = json.load(f)

    cloned = cloner.transform_product(product, transform_spec)
    if cloner.validate_payload(cloned):
        print("OK Transformed: Product will be assigned by SAP")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SAP Product Cloner - Usage Examples")
    print("=" * 60)

    example_1_simple_file_clone()
    example_2_bulk_transformation()

    print("\n" + "=" * 60)
    print("Examples Complete")
    print("=" * 60)
