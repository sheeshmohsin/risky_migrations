# Project 03 Safe: Adding Indexes Safely with CONCURRENTLY

This project demonstrates the **safe way** to add indexes to large tables in PostgreSQL using `CREATE INDEX CONCURRENTLY`.

## The Solution

Instead of using Django's default index creation (which locks the table), PostgreSQL offers `CREATE INDEX CONCURRENTLY` that:
1. Creates the index without blocking reads or writes
2. Takes longer to complete but causes **zero downtime**
3. Allows the application to continue serving traffic during index creation

## Comparison with proj03_indexes (Risky)

| Approach | Blocks Reads? | Blocks Writes? | Downtime | Use Case |
|----------|---------------|----------------|----------|----------|
| **Standard Index** (proj03_indexes) | ✅ Yes | ✅ Yes | Minutes | Small tables only |
| **CONCURRENTLY** (this project) | ❌ No | ❌ No | None | Production tables |

## Demo Setup (Docker)

### 1. Navigate to Project Directory

```bash
cd proj03_safe_backfill
```

### 2. Start Docker Containers

```bash
docker compose up --build -d
```

This starts:
- PostgreSQL 16 on port 5433
- Django app on port 8001

### 3. Seed the Tables

```bash
# Creates 10 rows in SmallEmail and 5,000,000 rows in LargeEmail (default)
docker compose exec web python manage.py seed_large_table

# Optional: Create fewer rows for faster testing
docker compose exec web python manage.py seed_large_table --large-count 1000000
```

### 4. Test the Endpoint

```bash
curl http://127.0.0.1:8001/list_large/
```

You should see JSON with email data.

## Demonstrating the Safe Migration

### Step 1: Check Current Migration State

```bash
docker compose exec web python manage.py showmigrations demoapp
```

You should see:
```
demoapp
 [X] 0001_initial
 [ ] 0002_add_email_index_concurrently
```

### Step 2: Run the Safe Index Creation Migration

```bash
docker compose exec web python manage.py migrate demoapp 0002
```

Watch the output. The migration uses `AddIndexConcurrently` which:
- Sets `atomic = False` (CONCURRENTLY can't run in a transaction)
- Creates indexes without blocking table access
- Takes longer than standard index creation, but no downtime

### Step 3: Verify No Table Locking During Migration

To prove the migration doesn't block queries:

1. **Terminal 1** - Rollback the migration first:
   ```bash
   docker compose exec web python manage.py migrate demoapp 0001
   ```

2. **Terminal 2** - Start continuous queries (keep running):
   ```bash
   while true; do
     curl http://127.0.0.1:8001/list_large/ && echo " - $(date)"
     sleep 1
   done
   ```

3. **Terminal 1** - Run the CONCURRENTLY migration:
   ```bash
   docker compose exec web python manage.py migrate demoapp 0002
   ```

4. **Observe Terminal 2**: Notice the queries **continue to work** during the entire migration!

This is the key difference from proj03_indexes where queries would hang.

## How It Works

### The Migration File

```python
# demoapp/migrations/0002_add_email_index_concurrently.py
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import models

class Migration(migrations.Migration):
    atomic = False  # Required for CONCURRENTLY

    operations = [
        AddIndexConcurrently(
            model_name='largeemail',
            index=models.Index(fields=['email'], name='large_email_email_idx'),
        ),
    ]
```

### Key Points

1. **`atomic = False`**: CONCURRENTLY operations cannot run inside a transaction
2. **`AddIndexConcurrently`**: PostgreSQL-specific operation from `django.contrib.postgres`
3. **Takes longer**: Index is built in multiple phases to avoid locks
4. **Safe for production**: Zero downtime, traffic continues uninterrupted

## Migration Commands Reference

### Check Migration Status
```bash
docker compose exec web python manage.py showmigrations demoapp
```

### Migrate Forward (Create Index Safely)
```bash
# Migrate to the CONCURRENTLY migration
docker compose exec web python manage.py migrate demoapp 0002

# Or migrate all pending migrations
docker compose exec web python manage.py migrate
```

### Migrate Backward (Drop Index)
```bash
# Rollback to migration 0001 (removes index)
docker compose exec web python manage.py migrate demoapp 0001
```

### Check Index in PostgreSQL
```bash
# Connect to PostgreSQL
docker compose exec db psql -U postgres -d risky_migrations

# List indexes on large_email table
\d large_email

# Exit psql
\q
```

## Local Development (Without Docker)

If you prefer to run locally:

### 1. Activate Virtual Environment

```bash
cd proj03_safe_backfill
source ../venv/bin/activate
```

### 2. Set Up PostgreSQL

You need a local PostgreSQL instance. Update `.env` with your connection details or use defaults:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Seed Data

```bash
python manage.py seed_large_table --large-count 1000000
```

### 5. Start Server

```bash
python manage.py runserver 8001
```

## Key Takeaways

- ✅ **CONCURRENTLY**: Creates indexes without blocking reads or writes
- ✅ **Zero downtime**: Application continues serving traffic during index creation
- ⏱️ **Takes longer**: Index is built in multiple phases (acceptable tradeoff)
- 🐘 **PostgreSQL only**: Not available in SQLite or MySQL
- 🔒 **atomic = False**: Required because CONCURRENTLY can't run in a transaction
- 📊 **Production-ready**: Safe for large tables with millions of rows

## When to Use This Approach

✅ **Use CONCURRENTLY when:**
- Adding indexes to tables with millions of rows
- Deploying during business hours
- Zero downtime is required
- Using PostgreSQL (9.2+)

❌ **Don't use CONCURRENTLY when:**
- Table is small (< 100k rows) - standard index is fine
- Using SQLite or MySQL (not supported)
- In development/testing environments

## Clean Up and Restart

To completely reset the project:

```bash
# Stop and remove containers + volumes
docker compose down -v

# Rebuild and start fresh
docker compose up --build -d

# Re-seed data
docker compose exec web python manage.py seed_large_table
```

## Comparison Example

Run both projects side-by-side to see the difference:

**Terminal 1 - Risky (proj03_indexes)**:
```bash
cd proj03_indexes
python manage.py runserver 8000
# In another terminal: python manage.py migrate demoapp 0002
# Try: curl http://127.0.0.1:8000/list_large/ (will HANG)
```

**Terminal 2 - Safe (proj03_safe_backfill)**:
```bash
cd proj03_safe_backfill
docker compose up -d
# docker compose exec web python manage.py migrate demoapp 0002
# Try: curl http://127.0.0.1:8001/list_large/ (works fine!)
```
