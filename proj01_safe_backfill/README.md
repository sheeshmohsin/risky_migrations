# proj01_safe_backfill - Safe NOT NULL Constraint Migration

## Overview

This project demonstrates the **SAFE way** to add a NOT NULL constraint to an existing column in a production database with millions of rows. It contrasts with `proj01_add_column_default` which shows the risky approach.

## The Problem

Adding a NOT NULL constraint to a nullable column on a large table causes:
- **Full table scan** to validate all existing rows
- **Table-level lock** during validation (can take minutes)
- **Blocked queries** - all SELECT/UPDATE/DELETE operations wait
- **Production downtime** or timeouts

## The Safe Solution: Three-Step Migration

### Step 1: Add Nullable Column
First migration adds the column as nullable (no validation required):
```python
# Migration 0002
status = models.CharField(max_length=20, null=True, blank=True)
```
- **Fast**: No table scan, just metadata change
- **Non-blocking**: No locks on existing rows

### Step 2: Backfill in Batches
Data migration updates rows in small batches (10,000 rows at a time):
```python
# Migration 0003 (data migration)
batch_size = 10000
while LargeUser.objects.filter(status__isnull=True).exists():
    ids = list(LargeUser.objects.filter(status__isnull=True)
               .values_list('id', flat=True)[:batch_size])
    LargeUser.objects.filter(id__in=ids).update(status='active')
```
- **Short transactions**: Each batch commits separately
- **Non-blocking**: Other queries can run between batches
- **Interruptible**: Can pause/resume if needed

### Step 3: Add NOT NULL Constraint
Final migration adds the constraint (validation is instant since all rows have values):
```python
# Migration 0004
status = models.CharField(max_length=20, null=False, blank=False)
```
- **Fast**: PostgreSQL can skip validation if all rows have values
- **Safe**: Application already handles the field as required

## Why This Works

1. **Small transactions** - Each batch is < 1 second
2. **No long locks** - Other queries can run between batches
3. **Gradual rollout** - Production keeps running during backfill
4. **Zero downtime** - APIs remain responsive throughout

## Setup

### Prerequisites
- Docker and Docker Compose
- 10+ GB free disk space (for 10M rows)

### Start the Application

```bash
docker compose up -d --build
```

The application will:
- Start PostgreSQL 16
- Run Django migrations
- Start Django dev server on http://localhost:8001

### Seed the Database

```bash
# Seed with 10 million rows (takes ~5 minutes)
docker compose exec web python manage.py seed_large_table --large-count=10000000

# Or start with 1 million for faster testing
docker compose exec web python manage.py seed_large_table --large-count=1000000
```

## Testing the Migrations

### Current State
After initial setup, both tables have no `status` field:

```bash
# Check current state
docker compose exec web python manage.py migrate --list
```

### Step 1: Add Nullable Status Field

```bash
# Modify models.py to add nullable status field
# Then generate migration:
docker compose exec web python manage.py makemigrations

# Run migration (should be instant even on 10M rows):
docker compose exec web python manage.py migrate

# Test API still works:
curl http://localhost:8001/list_large/
```

### Step 2: Create Batch Backfill Migration

Create a data migration:
```bash
docker compose exec web python manage.py makemigrations --empty demoapp --name backfill_status_field
```

Edit the generated migration to add batch update logic (see migration 0003 in the final code).

Run the backfill:
```bash
# In terminal 1: Run the backfill migration
docker compose exec web python manage.py migrate

# In terminal 2: While migration runs, test API (should respond quickly!)
while true; do curl --max-time 3 http://localhost:8001/list_large/ && echo " - Success"; sleep 1; done
```

**Expected result**: API continues responding during the entire backfill! Each batch takes < 1 second, so queries are never blocked for long.

### Step 3: Add NOT NULL Constraint

```bash
# Modify models.py to make status field NOT NULL
# Then generate migration:
docker compose exec web python manage.py makemigrations

# Run migration (should be instant since all rows have values):
time docker compose exec web python manage.py migrate
```

## Comparing with Risky Approach

### Risky Way (proj01_add_column_default)
- Single migration changes nullable → NOT NULL directly
- **Result**: 40 seconds of table lock on 10M rows
- **Impact**: All queries blocked for 40 seconds

### Safe Way (this project)
- Three separate migrations
- **Result**: 100 batch updates of 1 second each
- **Impact**: Queries blocked for max 1 second at a time

## Key Files

- `demoapp/models.py` - SmallUser and LargeUser models
- `demoapp/migrations/0002_*.py` - Add nullable status field
- `demoapp/migrations/0003_backfill_status_field.py` - Batch backfill data migration
- `demoapp/migrations/0004_*.py` - Add NOT NULL constraint
- `demoapp/management/commands/seed_large_table.py` - Seeding script
- `demoapp/views.py` - `/list_large/` endpoint for testing locks

## Architecture

### Models
```python
class SmallUser(models.Model):
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, null=False, blank=False)  # After step 3

    class Meta:
        db_table = 'small_user'

class LargeUser(models.Model):
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, null=False, blank=False)  # After step 3

    class Meta:
        db_table = 'large_user'
```

### Database Tables
- `small_user` - 10 rows (for comparison)
- `large_user` - 10,000,000 rows (demonstrates the problem)

## Commands Reference

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f web

# Seed database
docker compose exec web python manage.py seed_large_table --large-count=10000000

# Make migrations
docker compose exec web python manage.py makemigrations

# Run migrations
docker compose exec web python manage.py migrate

# Revert migration
docker compose exec web python manage.py migrate demoapp 0001

# Delete migration files
docker compose exec web rm demoapp/migrations/0002_*.py

# Shell access
docker compose exec web python manage.py shell
docker compose exec db psql -U postgres -d risky_migrations

# Test API
curl http://localhost:8001/list_large/

# Test with timeout
curl --max-time 3 http://localhost:8001/list_large/
```

## PostgreSQL Commands

```bash
# Connect to database
docker compose exec db psql -U postgres -d risky_migrations

# Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('small_user', 'large_user')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Check row counts
SELECT 'small_user' as table, COUNT(*) FROM small_user
UNION ALL
SELECT 'large_user', COUNT(*) FROM large_user;

# Check how many rows have been backfilled
SELECT
    COUNT(*) as total_rows,
    COUNT(status) as rows_with_status,
    COUNT(*) - COUNT(status) as rows_without_status
FROM large_user;

# Check for locks during migration
SELECT pid, usename, state, query
FROM pg_stat_activity
WHERE datname = 'risky_migrations';
```

## Best Practices

1. **Always batch data migrations** - Never update millions of rows in one transaction
2. **Use small batch sizes** - 10,000 rows keeps transactions under 1 second
3. **Add indexes before backfill** - Speeds up the `WHERE status IS NULL` filter
4. **Monitor progress** - Add logging to track batch completion
5. **Make it idempotent** - Use `filter(status__isnull=True)` so migration can be re-run
6. **Test on staging first** - Verify timing with production-like data volume

## Cleanup

```bash
# Stop and remove containers
docker compose down

# Remove volumes (deletes database)
docker compose down -v
```

## Related Projects

- **proj01_add_column_default** - Shows the RISKY way (direct NOT NULL constraint)
- This project - Shows the SAFE way (nullable → backfill → NOT NULL)

## Conclusion

This three-step approach is the industry-standard way to add NOT NULL constraints to large tables in production:
1. Add nullable field (fast)
2. Backfill in batches (safe, non-blocking)
3. Add NOT NULL constraint (fast, since values already exist)

Total time is longer, but **zero downtime** because each operation is non-blocking!
