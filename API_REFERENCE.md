# Product Cloner API Reference

## ProductCloner Class

Main class for product cloning operations. Use this for both interactive and programmatic access.

### Initialization

```python
from product_cloner import ProductCloner

cloner = ProductCloner(config_file='config.json')
```

**Parameters:**
- `config_file` (str): Path to JSON config file. Auto-creates defaults if missing.

**Config Properties:**
- `sap_base_url`: SAP instance URL (e.g., `https://host:44300`)
- `sap_api_path`: OData API path (e.g., `/sap/opu/odata/sap/API_PRODUCT_SRV`)
- `username`: SAP login username
- `password`: SAP login password  
- `dry_run`: Boolean, when true no POSTs are sent
- `verify_ssl`: Boolean, SSL certificate verification

## Methods

### read_from_file(file_path: str) -> Dict[str, Any]

Load product data from local JSON file.

### read_from_sap_api(product_id: str, expand: bool = True) -> Dict[str, Any]

Fetch product from SAP OData API.

### transform_product(product: Dict[str, Any], transforms: Dict[str, Any]) -> Dict[str, Any]

Apply transformations to product data.

### validate_payload(product: Dict[str, Any]) -> bool

Validate product has required fields for creation.

### post_to_sap(product: Dict[str, Any], dry_run: bool = True) -> Optional[str]

POST product to SAP to create new material.

## Complete Workflow Example

```python
from product_cloner import ProductCloner
import json

cloner = ProductCloner('config.json')
product = cloner.read_from_file('sample.json')

transforms = {
    'fields': {
        'Product': '500',
        'ProductOldID': ''
    },
    'nested': {}
}

cloned = cloner.transform_product(product, transforms)

if cloner.validate_payload(cloned):
    with open('output.json', 'w') as f:
        json.dump({'d': cloned}, f, indent=2)
    cloner.post_to_sap(cloned, dry_run=False)
```

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| FileNotFoundError | File doesn't exist | Check file path |
| JSONDecodeError | Invalid JSON | Validate JSON format |
| ValueError | Missing SAP credentials | Set username/password in config |
| ConnectionError | Network issue | Check URL and internet |
| HTTPError 401 | Invalid credentials | Verify SAP credentials |
| Validation failed | Missing entities | Check source structure |

## Best Practices

1. **Always test with dry-run first**
2. **Validate before posting**
3. **Save transformed data for audit**
4. **Check logs after operations**
5. **Use environment variables for secrets**

## Performance

- File reads: <100ms
- Transformations: instant (in-memory)
- API calls: 1-3 seconds (network dependent)
- Dry-run overhead: ~0ms

## Version & Compatibility

- **Python:** 3.6+
- **Dependencies:** requests 2.25+
- **SAP:** API_PRODUCT_SRV (standard)
- **Platforms:** Windows, Linux, macOS
