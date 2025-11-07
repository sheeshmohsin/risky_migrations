# Project 03: Adding/Changing Indexes

This project demonstrates the risks of adding indexes to large tables in Django.

## The Problem

When you add an index (`db_index=True`) to a field on a large table, the migration will:
1. Create the index on the entire table
2. **Hold an exclusive lock** during index creation (on SQLite and some databases)
3. Block all reads and writes until complete
4. Take significant time on tables with millions of rows

On a table with 100 million rows, creating an index can take minutes and cause downtime.

## Demo Setup

### 1. Navigate to Project Directory

```bash
cd proj03_indexes
```

### 2. Activate Virtual Environment

```bash
source ../venv/bin/activate
```

### 3. Run Initial Migration

```bash
python manage.py migrate
```

### 4. Seed the Tables

```bash
# Creates 10 rows in SmallEmail and 100,000,000 rows in LargeEmail (default)
python manage.py seed_large_table

# Optional: Create fewer rows for faster testing
python manage.py seed_large_table --large-count 10000000
```

### 5. Start the Development Server

```bash
python manage.py runserver
```

Test the endpoint:
```bash
curl http://127.0.0.1:8000/list_large/
```

## Demonstrating the Risky Migration

The models already have `db_index=True` on the email field. This migration demonstrates adding an index to a large text column.

### Step 1: Check Current Migration State

```bash
python manage.py showmigrations demoapp
```

You should see:
```
demoapp
 [X] 0001_initial
 [ ] 0002_alter_largeemail_email_alter_smallemail_email
```

### Step 2: Run the Index Creation Migration

**Migration Up (Apply the index creation):**
```bash
python manage.py migrate demoapp 0002
```

Watch the timing output. You'll see:
- SmallEmail index created instantly (10 rows)
- LargeEmail index takes much longer (100M rows - causes table lock!)

**Migration Down (Rollback):**
```bash
python manage.py migrate demoapp 0001
```

This removes the index from both tables.

**Migration Up Again:**
```bash
python manage.py migrate demoapp 0002
```

### Step 3: Observe Table Locking During Migration

To demonstrate how this migration blocks queries:

1. **Terminal 1** - Rollback first:
   ```bash
   python manage.py migrate demoapp 0001
   ```

2. **Terminal 1** - Start the dev server:
   ```bash
   python manage.py runserver
   ```

3. **Terminal 2** - Try to query the table:
   ```bash
   curl http://127.0.0.1:8000/list_large/
   ```

   This should work fine (returns data).

4. **Terminal 3** - Run the migration:
   ```bash
   python manage.py migrate demoapp 0002
   ```

5. **Terminal 2** - Immediately try the curl again while migration is running:
   ```bash
   curl http://127.0.0.1:8000/list_large/
   ```

   Notice: The curl request **hangs** until the migration completes because the table is locked!

## The Safe Way (PostgreSQL Only)

On PostgreSQL, you can create indexes concurrently to avoid locks:

```python
from django.contrib.postgres.indexes import Index

class LargeEmail(models.Model):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=255)

    class Meta:
        indexes = [
            Index(fields=['email'], name='large_email_email_idx',
                  opclasses=['varchar_pattern_ops'], concurrent=True)
        ]
```

Or use a migration operation:

```python
from django.contrib.postgres.operations import AddIndexConcurrently

operations = [
    AddIndexConcurrently(
        model_name='largeemail',
        index=models.Index(fields=['email'], name='large_email_email_idx'),
    ),
]
```

**Benefits of CONCURRENTLY:**
- Index is built without blocking reads or writes
- Takes longer to create, but no downtime
- Only available in PostgreSQL

**Note:** SQLite doesn't support concurrent index creation, so this demo uses the standard approach which does cause locking.

## Key Takeaways

- ✅ **SmallEmail**: Index creation is instant (10 rows)
- ❌ **LargeEmail**: Index creation takes time and locks the table (100M rows)
- 🔒 During migration, all queries to the table are **blocked**
- 📊 The `/list_large/` endpoint demonstrates real-world impact of table locks
- 🐘 **PostgreSQL users**: Use `CONCURRENTLY` to avoid locks

## Migration Commands Reference

### Check Migration Status
```bash
python manage.py showmigrations demoapp
```

### Migrate Forward (Create Index)
```bash
# Migrate to a specific migration
python manage.py migrate demoapp 0002

# Or migrate all pending migrations
python manage.py migrate
```

### Migrate Backward (Drop Index)
```bash
# Rollback to migration 0001 (removes index)
python manage.py migrate demoapp 0001
```

### Fake Migration (Mark as applied without running)
```bash
# Mark migration as applied without actually running it
python manage.py migrate demoapp 0002 --fake

# Useful for testing or when schema is already correct
```

## Clean Up and Restart

To start fresh:

```bash
# Delete database
rm db.sqlite3

# Delete all migrations except __init__.py
rm demoapp/migrations/0*.py

# Recreate migrations
python manage.py makemigrations
python manage.py migrate

# Re-seed data
python manage.py seed_large_table
```
