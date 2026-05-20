# SAP Product Clone Automation Tool

Automates the read → modify → create workflow for SAP products using the `API_PRODUCT_SRV` OData service.

## Quick Start

### 1. Install Dependencies
```bash
pip install requests
```

### 2. Configure SAP Credentials
Edit `config.json` with your SAP credentials:
```json
{
  "username": "your_sap_user",
  "password": "your_sap_password",
  "sap_base_url": "https://YOUR_SAP_INSTANCE",
  "dry_run": true
}
```

### 3. Run Interactive Mode
```bash
python product_cloner.py
```

Follow the prompts to:
1. Select source (local file or SAP API)
2. Enter new product details
3. Review transformation
4. Validate payload
5. Save and/or POST to SAP

## Usage

### Interactive Mode (Default)
```bash
python product_cloner.py
```
Best for one-off cloning with user interaction.

### Batch Mode
```bash
python product_cloner.py --batch OP_API_PRODUCT_SRV_0001.json --config config.json --no-dry-run
```

Options:
- `--batch FILE`: Process file in batch mode
- `--config FILE`: Use custom config (default: config.json)
- `--no-dry-run`: Actually POST to SAP (default: dry-run only)

## Features

✅ **Read flexibility** - Local files OR SAP API  
✅ **Deep copy** - Preserves all nested structures  
✅ **Transform logic** - Field-by-field control  
✅ **Validation** - Ensures payload completeness  
✅ **Dry-run** - Preview before committing  
✅ **Logging** - Full audit trail
✅ **Error handling** - Clear error messages
