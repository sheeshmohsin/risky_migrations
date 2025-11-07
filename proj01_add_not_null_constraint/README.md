# Project 01: Adding NOT NULL Constraint

This project demonstrates the risks of adding a NOT NULL constraint to an existing nullable column on a large table in Django.

## The Problem

When you change a nullable column to NOT NULL (e.g., `null=True` → `null=False`), PostgreSQL must:
1. **Validate every existing row** to ensure no NULLs exist
2. Hold a **table-level lock** during this validation
3. Block all reads and writes until validation completes
4. On tables with millions of rows, this can take significant time

On a table with millions of rows, this can cause significant downtime.

## Demo Setup

You can run this project either with Docker (recommended) or locally with a virtual environment.

### Option A: Docker Setup (Recommended)

#### 1. Navigate to Project Directory

```bash
cd proj01_add_not_null_constraint
```

#### 2. Start Docker Containers

```bash
# Build and start the containers
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

This will:
- Start a PostgreSQL 16 database container
- Build and start the Django application container
- Automatically run migrations
- Start the Django development server on port 8000

#### 3. Seed the Tables

```bash
# In a new terminal, run the seed command
docker-compose exec web python manage.py seed_large_table

# Optional: Create fewer rows for faster testing (10 million instead of 100 million)
docker-compose exec web python manage.py seed_large_table --large-count 10000000
```

#### 4. Test the Endpoint

```bash
curl http://127.0.0.1:8000/list_large/
```

#### 5. Stop Containers

```bash
# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (deletes database)
docker-compose down -v
```

#### Access PostgreSQL Directly

```bash
# Connect to the database
docker-compose exec db psql -U postgres -d risky_migrations

# View tables
\dt

# Check row counts
SELECT COUNT(*) FROM large_user;
SELECT COUNT(*) FROM small_user;
```

### Option B: Local Setup with Virtual Environment

#### 1. Navigate to Project Directory

```bash
cd proj01_add_not_null_constraint
```

#### 2. Activate Virtual Environment

```bash
source ../venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Setup PostgreSQL Locally

Make sure PostgreSQL is installed and running, then create a database:
```bash
createdb risky_migrations
```

Update `.env` file with your local PostgreSQL settings:
```bash
POSTGRES_HOST=localhost
```

#### 5. Run Initial Migration

```bash
python manage.py migrate
```

#### 6. Seed the Tables

```bash
# Creates 10 rows in SmallUser and 100,000,000 rows in LargeUser (default)
python manage.py seed_large_table

# Optional: Create fewer rows for faster testing
python manage.py seed_large_table --large-count 10000000
```

#### 7. Start the Development Server

```bash
python manage.py runserver
```

Test the endpoint:
```bash
curl http://127.0.0.1:8000/list_large/
```

## Demonstrating the Risky Migration

The models already have the `status` field with `default="active"` added. This migration demonstrates the WRONG way to add a column.

### Step 1: Check Current Migration State

**Docker:**
```bash
docker-compose exec web python manage.py showmigrations demoapp
```

**Local:**
```bash
python manage.py showmigrations demoapp
```

You should see:
```
demoapp
 [X] 0001_initial
 [ ] 0002_largeuser_status_smalluser_status
```

### Step 2: Run the Risky Migration

**Migration Up (Apply the risky migration):**

Docker:
```bash
docker-compose exec web python manage.py migrate demoapp 0002
```

Local:
```bash
python manage.py migrate demoapp 0002
```

Watch the timing output. You'll see:
- SmallUser field added instantly (10 rows)
- LargeUser field takes much longer (100M rows - causes table lock!)

**Migration Down (Rollback):**

Docker:
```bash
docker-compose exec web python manage.py migrate demoapp 0001
```

Local:
```bash
python manage.py migrate demoapp 0001
```

This removes the status field from both tables.

### Step 3: Observe Table Locking During Migration

To demonstrate how this migration blocks queries:

**For Docker:**

1. **Terminal 1** - Rollback first:
   ```bash
   docker-compose exec web python manage.py migrate demoapp 0001
   ```

2. **Terminal 1** - Server should already be running from docker-compose

3. **Terminal 2** - Try to query the table:
   ```bash
   curl http://127.0.0.1:8000/list_large/
   ```

   This should work fine (returns data).

4. **Terminal 3** - Run the migration:
   ```bash
   docker-compose exec web python manage.py migrate demoapp 0002
   ```

5. **Terminal 2** - Immediately try the curl again while migration is running:
   ```bash
   curl http://127.0.0.1:8000/list_large/
   ```

   Notice: The curl request **hangs** until the migration completes because the table is locked!

**For Local:**

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

## The Safe Way: Adding a Column the Right Way

The `role` field demonstrates the **SAFE** approach to adding a column with a default value.

### Three-Step Migration Process

**Step 1: Add the field as nullable (Migration 0003)**
```python
role = models.CharField(max_length=20, null=True, blank=True)
```

Run migration:

Docker:
```bash
docker-compose exec web python manage.py migrate demoapp 0003
```

Local:
```bash
python manage.py migrate demoapp 0003
```

This is **fast** - no table rewrite, no locks!

**Step 2: Backfill in batches (Migration 0004)**

The data migration backfills the `role` field in batches:

```python
batch_size = 1000000  # 1 million rows per batch
while True:
    ids_to_update = list(
        LargeUser.objects.filter(role__isnull=True).values_list('id', flat=True)[:batch_size]
    )
    if not ids_to_update:
        break
    LargeUser.objects.filter(id__in=ids_to_update).update(role='user')
```

Run migration:

Docker:
```bash
docker-compose exec web python manage.py migrate demoapp 0004
```

Local:
```bash
python manage.py migrate demoapp 0004
```

This is **safe** - short transactions, no long locks!

**Step 3: Enforce NOT NULL constraint (Migration 0005)**
```python
role = models.CharField(max_length=20, default="user")
```

Run migration:

Docker:
```bash
docker-compose exec web python manage.py migrate demoapp 0005
```

Local:
```bash
python manage.py migrate demoapp 0005
```

This is **fast** - all rows already have values, just enforcing the constraint!

### Compare the Approaches

**WRONG Way (status field - Migration 0002):**
- ❌ Single migration adds column + default + rewrites table
- ❌ Holds exclusive lock during entire operation
- ❌ Blocks all queries for 30+ seconds on 100M rows

**RIGHT Way (role field - Migrations 0003, 0004, 0005):**
- ✅ Step 1: Add nullable column (instant)
- ✅ Step 2: Backfill in batches (safe, no long locks)
- ✅ Step 3: Enforce NOT NULL (instant, data already populated)

### Test the Safe Approach

Rollback to before the role migrations:

Docker:
```bash
docker-compose exec web python manage.py migrate demoapp 0002
```

Local:
```bash
python manage.py migrate demoapp 0002
```

Then migrate forward step by step:

Docker:
```bash
# Step 1: Add nullable column
docker-compose exec web python manage.py migrate demoapp 0003

# Step 2: Backfill in batches
docker-compose exec web python manage.py migrate demoapp 0004

# Step 3: Enforce NOT NULL
docker-compose exec web python manage.py migrate demoapp 0005
```

Local:
```bash
# Step 1: Add nullable column
python manage.py migrate demoapp 0003

# Step 2: Backfill in batches
python manage.py migrate demoapp 0004

# Step 3: Enforce NOT NULL
python manage.py migrate demoapp 0005
```

Notice how the `/list_large/` endpoint remains responsive during the backfill!

## Key Takeaways

### Wrong Way (status field)
- ❌ **LargeUser**: Migration takes 30+ seconds and locks the table (100M rows)
- 🔒 During migration, all queries to the table are **blocked**
- 📊 The `/list_large/` endpoint hangs during migration

### Right Way (role field)
- ✅ **Step 1**: Add nullable column (instant, no locks)
- ✅ **Step 2**: Backfill in batches (safe, short transactions)
- ✅ **Step 3**: Enforce NOT NULL (instant, data already there)
- 🚀 The `/list_large/` endpoint remains responsive throughout!

## Migration Commands Reference

### Check Migration Status
```bash
python manage.py showmigrations demoapp
```

### Migrate Forward (Apply Migration 0002)
```bash
# Migrate to a specific migration
python manage.py migrate demoapp 0002

# Or migrate all pending migrations
python manage.py migrate
```

### Migrate Backward (Rollback Migration 0002)
```bash
# Rollback to migration 0001 (removes status field)
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
