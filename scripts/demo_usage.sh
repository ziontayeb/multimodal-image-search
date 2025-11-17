#!/bin/bash
# Demo script showing how to use manage_db.py

echo "========================================="
echo "Database Management Demo"
echo "========================================="
echo ""

# Navigate to project directory
cd "$(dirname "$0")/.."

echo "1. Show current database statistics:"
echo "$ python scripts/manage_db.py stats"
python scripts/manage_db.py stats
echo ""

echo "========================================="
echo ""
echo "2. List current images (first few):"
echo "$ python scripts/manage_db.py list"
python scripts/manage_db.py list
echo ""

echo "========================================="
echo ""
echo "Example commands you can run:"
echo ""
echo "# Add a single image WITH caption generation:"
echo "$ python scripts/manage_db.py add --path /path/to/your/image.jpg --caption"
echo ""

echo "# Add all images from a directory WITH captions:"
echo "$ python scripts/manage_db.py add --dir /path/to/your/images --caption"
echo ""

echo "# Add images WITHOUT caption generation (faster):"
echo "$ python scripts/manage_db.py add --dir /path/to/your/images"
echo ""

echo "# Get detailed info about an image:"
echo "$ python scripts/manage_db.py info --path /path/to/your/image.jpg"
echo ""

echo "# Delete an image:"
echo "$ python scripts/manage_db.py delete --path /path/to/your/image.jpg"
echo ""

echo "# List all images with their captions:"
echo "$ python scripts/manage_db.py list --captions"
echo ""

echo "# Export captions for evaluation:"
echo "$ python scripts/manage_db.py export-captions --output my_captions.json"
echo ""

echo "# Wipe entire database to start over:"
echo "$ python scripts/manage_db.py wipe --all"
echo ""

echo "# Wipe only Pinecone vectors (keep captions):"
echo "$ python scripts/manage_db.py wipe --pinecone"
echo ""

echo "# Wipe only caption database (keep Pinecone):"
echo "$ python scripts/manage_db.py wipe --captions"
echo ""

echo "========================================="
echo "For full help, run:"
echo "$ python scripts/manage_db.py --help"
echo "$ python scripts/manage_db.py add --help"
echo "$ python scripts/manage_db.py wipe --help"
echo "========================================="
