#!/usr/bin/env python3
"""
Migration script to add lifestyle quiz columns to the users table.
Run this on Railway with: python scripts/migrate_lifestyle.py
"""
import os
import sys

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

# Handle Railway's postgres:// vs postgresql:// issue
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to database...")

from sqlalchemy import create_engine, text

engine = create_engine(DATABASE_URL)

# New columns to add
NEW_COLUMNS = [
    ("region", "VARCHAR"),
    ("activity_level", "VARCHAR"),
    ("work_environment", "VARCHAR"),
    ("diet_type", "VARCHAR"),
    ("bedtime", "VARCHAR"),
    ("wake_time", "VARCHAR"),
    ("chronotype", "VARCHAR"),
    ("height_feet", "INTEGER"),
    ("height_inches", "INTEGER"),
    ("weight_lbs", "FLOAT"),
]

with engine.connect() as conn:
    # Get existing columns
    result = conn.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
    """))
    existing_columns = [row[0] for row in result.fetchall()]
    print(f"Existing columns: {existing_columns}")

    # Add missing columns
    for col_name, col_type in NEW_COLUMNS:
        if col_name not in existing_columns:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"✓ Added column: {col_name}")
            except Exception as e:
                print(f"✗ Error adding {col_name}: {e}")
        else:
            print(f"- Column already exists: {col_name}")

print("\n✅ Migration complete!")
