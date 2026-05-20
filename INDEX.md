# SAP Product Cloner - Complete Toolkit

## 📌 Start Here

Welcome! This is a complete automation toolkit for cloning SAP products using the `API_PRODUCT_SRV` OData service.

**👉 If you're new:** Start with **QUICKSTART.md**  
**👉 If you're integrating:** Check **API_REFERENCE.md**  
**👉 If you want details:** Read **README.md**

## 🎯 What Does This Do?

Automates the **read → transform → validate → create** workflow.

## Features

✅ Flexible input — Files or live SAP API  
✅ Safe by default — Dry-run mode prevents mistakes  
✅ Well tested — Includes test suite & examples  
✅ Fully documented — 5 guides + API docs  
✅ Production ready — Error handling, logging, validation  
✅ Extensible — Easy to customize transformations  

## Quick Reference

### Interactive Mode
```bash
python product_cloner.py
```

### Batch Mode
```bash
python product_cloner.py --batch sample.json --config config.json
```

### Test
```bash
python test_cloner.py
python examples.py
```
