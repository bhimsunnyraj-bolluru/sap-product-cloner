# Quick Start Guide - SAP Product Cloner

## What This Tool Does
Automates the SAP product cloning workflow:
- **Read** existing product (from file or SAP API)
- **Transform** product data (change ID, description, pricing, etc.)
- **Validate** the new product payload
- **Create** new product in SAP via API

## Installation

### 1. Install Python Dependencies
```bash
pip install requests
```

### 2. Verify Setup
```bash
python test_cloner.py
```

You should see all tests passing (✓).

## Configuration

### For API Access
Edit `config.json` with your SAP credentials:

```json
{
  "sap_base_url": "https://YOUR_SAP_INSTANCE:44300",
  "sap_api_path": "/sap/opu/odata/sap/API_PRODUCT_SRV",
  "username": "your_username",
  "password": "your_password",
  "dry_run": true,
  "verify_ssl": false
}
```

## Usage

### Interactive Mode
```bash
python product_cloner.py
```

**Flow:**
1. Choose source: Load from file OR fetch from SAP API
2. Enter product details: New ID, description, GTIN
3. Review transformation preview
4. Validate payload
5. Save to file (optional)
6. POST to SAP (optional)

### Batch Mode
```bash
python product_cloner.py --batch sample.json --config config.json
```

## Security Notes

⚠️ **Never commit `config.json` with real credentials!**

Use git to ignore it:
```bash
echo config.json >> .gitignore
git rm --cached config.json
```
