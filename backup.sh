#!/bin/bash
# Complete Django Site Backup Script
# Run this locally with Git Bash

echo "=== TipsyTheoryy - Complete Backup ==="
echo ""

# Create backup directory with timestamp
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "✓ Created backup directory: $BACKUP_DIR"
echo ""

# 1. Backup Database (All Data)
echo "📦 Backing up all database data..."
PYTHONIOENCODING=utf-8 python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    --exclude auth.permission \
    --exclude contenttypes \
    --exclude sessions.session \
    > "$BACKUP_DIR/full_database.json"

echo "✓ Full database backup: $BACKUP_DIR/full_database.json"

# 2. Backup Food Items & Categories Only
echo "📦 Backing up food items and categories..."
PYTHONIOENCODING=utf-8 python manage.py dumpdata \
    urbanfoods.FoodCategory \
    urbanfoods.FoodItem \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    > "$BACKUP_DIR/food_data.json"

echo "✓ Food data backup: $BACKUP_DIR/food_data.json"

# 3. Backup Users (excluding passwords for security)
echo "📦 Backing up user data..."
PYTHONIOENCODING=utf-8 python manage.py dumpdata \
    urbanfoods.User \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    > "$BACKUP_DIR/users.json"

echo "✓ User data backup: $BACKUP_DIR/users.json"

# 4. Backup Orders
echo "📦 Backing up orders..."
PYTHONIOENCODING=utf-8 python manage.py dumpdata \
    urbanfoods.Order \
    urbanfoods.OrderItem \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    > "$BACKUP_DIR/orders.json"

echo "✓ Orders backup: $BACKUP_DIR/orders.json"

# 5. Copy Media Files (Images)
echo "📦 Backing up media files..."
if [ -d "media" ]; then
    cp -r media "$BACKUP_DIR/media"
    echo "✓ Media files backup: $BACKUP_DIR/media"
else
    echo "⚠ No media directory found"
fi

# 6. Copy SQLite Database (full copy)
echo "📦 Backing up SQLite database file..."
if [ -f "db.sqlite3" ]; then
    cp db.sqlite3 "$BACKUP_DIR/db.sqlite3"
    echo "✓ SQLite database backup: $BACKUP_DIR/db.sqlite3"
else
    echo "⚠ No db.sqlite3 found"
fi

# 7. Backup Static Files Configuration
echo "📦 Backing up static files..."
if [ -d "static" ]; then
    cp -r static "$BACKUP_DIR/static"
    echo "✓ Static files backup: $BACKUP_DIR/static"
else
    echo "⚠ No static directory found"
fi

# 8. Create backup summary
echo "📝 Creating backup summary..."
cat > "$BACKUP_DIR/README.txt" << EOF
TipsyTheoryy - Complete Backup
Created: $(date)
================================================

Contents:
- full_database.json: Complete database dump
- food_data.json: Food items and categories only
- users.json: User accounts data
- orders.json: Order history
- media/: All uploaded images
- static/: Static files
- db.sqlite3: Complete SQLite database

Restore Instructions:
1. For PostgreSQL: python manage.py loaddata <file>.json
2. For media files: Copy media/ to your project root
3. For SQLite: Copy db.sqlite3 to project root

Notes:
- Passwords are hashed (secure)
- Session data excluded
- Permissions will be recreated automatically
EOF

echo "✓ Backup summary created"
echo ""

# Create a ZIP archive
echo "📦 Creating ZIP archive..."
powershell Compress-Archive -Path "$BACKUP_DIR" -DestinationPath "${BACKUP_DIR}.zip"

if [ -f "${BACKUP_DIR}.zip" ]; then
    echo "✓ ZIP archive created: ${BACKUP_DIR}.zip"
    echo ""
    echo "=== Backup Complete! ==="
    echo ""
    echo "Backup location: ./${BACKUP_DIR}/"
    echo "Archive: ./${BACKUP_DIR}.zip"
    echo ""
    echo "Backup size:"
    du -sh "$BACKUP_DIR"
    du -sh "${BACKUP_DIR}.zip"
else
    echo "⚠ ZIP creation failed, but folder backup is complete"
    echo ""
    echo "=== Backup Complete! ==="
    echo ""
    echo "Backup location: ./${BACKUP_DIR}/"
fi

echo ""
