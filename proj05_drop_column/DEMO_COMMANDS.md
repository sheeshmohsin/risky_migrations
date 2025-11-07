# Demo Commands for proj05_drop_column

This file contains step-by-step commands to demonstrate the **RISKY** practice of dropping database columns without first removing all code references.

## Prerequisites

Ensure Docker and Docker Compose are installed on your system.

---

## Overview

This project demonstrates **why you must remove all code references BEFORE dropping a column**:

1. **Migration 0001**: Initial state with `legacy_code` column on both SmallProduct and LargeProduct tables
2. **Migration 0002**: **RISKY** - Drops `legacy_code` column directly from database

This project includes two API endpoints to demonstrate the impact:
- `/list_large/` - Uses `.values('id', 'name', 'price')` to fetch only specific fields (SAFE - continues working)
- `/search_by_legacy_code/` - Uses `.filter(legacy_code=...)` to query by the dropped column (BREAKS - returns HTTP 500)

---

## Step 1: Start the Containers

```bash
cd proj05_drop_column
docker compose up --build -d
```

This will:
- Start PostgreSQL 16 database on port 5435
- Build and start Django application
- Start Django dev server on http://localhost:8003

---

## Step 2: Reset to Initial State

The containers start with all migrations applied. Let's reset to the beginning:

```bash
# Rollback to initial migration
docker compose exec web python manage.py migrate demoapp 0001
```

Verify migration status:

```bash
docker compose exec web python manage.py showmigrations demoapp
```

Expected output:
```
demoapp
 [X] 0001_initial
 [ ] 0002_remove_largeproduct_legacy_code_and_more
```

---

## Step 3: Seed the Database

Seed with 10 million rows for a realistic demonstration:

```bash
docker compose exec web python manage.py seed_large_table --large-count 10000000
```

**Note:** This takes about 4-5 minutes with the optimized batch size of 10,000 rows.

For faster testing (1 million rows, ~30 seconds):

```bash
docker compose exec web python manage.py seed_large_table --large-count 1000000
```

Verify the data:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "SELECT COUNT(*) FROM large_product;"
```

Expected output:
```
  count
----------
 10000000
```

---

## Step 4: Test Both Endpoints (Before Dropping Column)

### Test the safe endpoint:
```bash
curl http://127.0.0.1:8003/list_large/
```

Expected response (fast, < 1 second):
```json
{
  "products": [
    {"id": 1, "name": "LargeProduct_1", "legacy_code": "N/A", "price": "99.99"},
    ...
  ],
  "count": 10
}
```

### Test the risky endpoint:
```bash
curl "http://127.0.0.1:8003/search_by_legacy_code/?code=LEGACY-001"
```

Expected response (should work before migration):
```json
{
  "query": "LEGACY-001",
  "products": [
    {"id": 1, "name": "LargeProduct_1", "legacy_code": "LEGACY-001", "price": "99.99"},
    ...
  ],
  "count": 10
}
```

**Observation:** Both endpoints work correctly when the column exists!

---

## Step 5: Monitor Both APIs Continuously

Open a **second terminal** and run this monitoring script to continuously ping both APIs:

```bash
while true; do
  echo "[$(date +%H:%M:%S)] Testing APIs";

  # Test list_large endpoint (should always work - uses .values())
  if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8003/list_large/)" = "200" ]; then
    echo " ✅ /list_large/ SUCCESS";
  else
    echo " ❌ /list_large/ FAILED";
  fi

  # Test search_by_legacy_code endpoint (will fail after migration 0002)
  if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 'http://127.0.0.1:8003/search_by_legacy_code/?code=LEGACY-001')" = "200" ]; then
    echo " ✅ /search_by_legacy_code/ SUCCESS";
  else
    echo " ❌ /search_by_legacy_code/ FAILED";
  fi

  echo "";
  sleep 1;
done
```

**Before migration 0002:**
```
[21:45:01] Testing APIs
 ✅ /list_large/ SUCCESS
 ✅ /search_by_legacy_code/ SUCCESS
```

---

## Step 6: Run Migration 0002 - Drop Column (RISKY!)

In your **first terminal**, run the migration to drop the `legacy_code` column:

```bash
docker compose exec web python manage.py migrate demoapp 0002
```

Expected output:
```
Operations to perform:
  Target specific migration: 0002_remove_largeproduct_legacy_code_and_more, from demoapp
Running migrations:
  Applying demoapp.0002_remove_largeproduct_legacy_code_and_more...

[2025-11-07 21:45:15.123] Dropping legacy_code column from SmallProduct...
[2025-11-07 21:45:15.145] ✓ SmallProduct column dropped

[2025-11-07 21:45:15.146] Dropping legacy_code column from LargeProduct...
[2025-11-07 21:45:15.234] ✓ LargeProduct column dropped
 OK
```

**Observation:** Migration completes instantly (< 1 second) even for 10 million rows!

Why it's fast:
- Dropping a column in PostgreSQL is a metadata-only operation
- No table rewrite needed
- No data scanning required

---

## Step 7: Observe API Behavior After Migration

Watch your **second terminal** (monitoring script):

**After migration 0002:**
```
[21:45:16] Testing APIs
 ✅ /list_large/ SUCCESS
 ❌ /search_by_legacy_code/ FAILED

[21:45:17] Testing APIs
 ✅ /list_large/ SUCCESS
 ❌ /search_by_legacy_code/ FAILED
```

**Key Observation:**
- ✅ `/list_large/` continues to work because it uses `.values('id', 'name', 'price')` to explicitly specify fields
- ❌ `/search_by_legacy_code/` fails with HTTP 500 because it tries to filter by `legacy_code` which no longer exists

---

## Step 8: Inspect the Errors

Check the error in detail:

```bash
curl "http://127.0.0.1:8003/search_by_legacy_code/?code=LEGACY-001"
```

You'll see a Django error page with:
```
FieldError at /search_by_legacy_code/
Cannot resolve keyword 'legacy_code' into field. Choices are: id, name, price
```

Check Django logs:

```bash
docker compose logs web
```

You'll see the stack trace showing the `FieldError` exception.

---

## Step 9: Verify Column is Dropped in Database

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_product"
```

Expected output (no `legacy_code` column):
```
                         Table "public.large_product"
  Column  |          Type          | Collation | Nullable | Default
----------+------------------------+-----------+----------+---------
 id       | bigint                 |           | not null |
 name     | character varying(100) |           | not null |
 price    | numeric(10,2)          |           | not null |
```

The `legacy_code` column is gone from the database!

---

## Step 10: The SAFE Way to Drop Columns

This project demonstrates the **WRONG WAY** (drop column immediately). Here's the **RIGHT WAY**:

### Safe Column Drop Process (3 Steps):

**Step 1: Remove all code references**
- Update all queries, views, forms, serializers to stop using `legacy_code`
- Deploy the code changes
- Wait for all application servers to restart

**Step 2: Mark column as deprecated (optional)**
- Add a new migration to make column nullable: `legacy_code = CharField(null=True, blank=True)`
- This signals "we're planning to drop this"
- Deploy and monitor

**Step 3: Drop the column**
- Only after confirming zero code references
- Run migration to drop column: `RemoveField('largeproduct', 'legacy_code')`
- This is now safe because no code tries to use it

### Timeline Comparison:

**RISKY Approach (This Project):**
```
0:00 [DROP COLUMN] ──────────────────────────────── 0:01
     ❌ Instant application breakage
     ❌ HTTP 500 errors on affected endpoints
     ❌ No rollback path (data is gone)
```

**SAFE Approach (Recommended):**
```
Day 1: Remove code references ──→ Deploy ──→ Monitor
Day 2: (Optional) Mark deprecated ──→ Deploy ──→ Monitor
Day 7: Drop column ──→ Deploy
       ✅ Zero downtime
       ✅ No application errors
       ✅ Safe rollback before final drop
```

---

## Additional Commands

### Check which endpoints are affected:

```bash
# Search for legacy_code usage in views
docker compose exec web grep -n "legacy_code" demoapp/views.py
```

Output:
```
17:            'legacy_code': 'N/A',  # Always N/A since we're not fetching it
35:    products = LargeProduct.objects.filter(legacy_code=legacy_code)[:10]
41:            'legacy_code': p.legacy_code,
```

Line 35 and 41 are the problematic lines that cause the failure!

### Check model definition:

```bash
docker compose exec web python manage.py shell
```

```python
from demoapp.models import LargeProduct
# Check available fields
print(LargeProduct._meta.get_fields())
# Output: [id, name, price]  # No legacy_code!

# Try to filter by legacy_code
LargeProduct.objects.filter(legacy_code='test')
# Raises: FieldError: Cannot resolve keyword 'legacy_code' into field
```

### Monitor active queries:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT pid, usename, state, query_start, query
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state != 'idle'
ORDER BY query_start;
"
```

### Check table sizes:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('small_product', 'large_product');
"
```

Expected output (10M rows):
```
 schemaname |   tablename   |  size
------------+---------------+---------
 public     | small_product | 16 kB
 public     | large_product | 730 MB
```

---

## Cleanup

### Reset to beginning:

```bash
docker compose exec web python manage.py migrate demoapp 0001
docker compose exec web python manage.py seed_large_table --large-count 10000000
```

### Stop containers:

```bash
docker compose down
```

### Stop and remove data (deletes database):

```bash
docker compose down -v
```

### Restart fresh:

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate demoapp 0001
docker compose exec web python manage.py seed_large_table --large-count 10000000
```

---

## Key Takeaways

### ❌ What This Project Shows (WRONG WAY)

**Dropping columns without removing code references causes:**
- Immediate application breakage (HTTP 500 errors)
- FieldError exceptions on affected endpoints
- No graceful degradation
- Difficult rollback (need to restore data)

**Why migration 0002 is instant:**
- PostgreSQL DROP COLUMN is metadata-only (in most cases)
- No table rewrite needed
- No data scanning
- Completes in < 1 second even for 10M rows

### ✅ Safe Column Drop Pattern (RIGHT WAY)

**Always follow this order:**

1. **Code First** - Remove all references to the column in application code
2. **Deploy Code** - Deploy and verify no errors
3. **Monitor** - Wait and observe production traffic
4. **Database Last** - Drop the column in database migration

**Why `.values()` is safer:**
```python
# UNSAFE - tries to fetch ALL model fields (including dropped ones)
products = LargeProduct.objects.all()[:10]
for p in products:
    print(p.legacy_code)  # BREAKS if column dropped

# SAFE - explicitly specifies which fields to fetch
products = LargeProduct.objects.values('id', 'name', 'price')[:10]
for p in products:
    print(p['name'])  # Works even if other columns are dropped
```

### 📊 Impact Summary

| Metric | DROP COLUMN (10M rows) |
|--------|------------------------|
| Migration Duration | < 1 second |
| Table Lock Duration | < 1 second |
| Application Impact | **IMMEDIATE BREAKAGE** |
| HTTP 500 Errors | All endpoints using dropped column |
| Rollback Safety | **RISKY** (data is deleted) |
| Production Ready | ❌ No (must remove code first) |

### 🎯 When to Use This Pattern

**NEVER drop a column before removing code references!**

Always use the safe 3-step process:
1. Remove code references → Deploy
2. (Optional) Mark column as deprecated → Deploy
3. Drop column → Deploy

**The only exception:**
- Column was added in a recent migration that never deployed to production
- Confirmed zero production usage
- Can safely drop immediately

---

## Troubleshooting

### APIs not showing as failed in monitoring script:

Make sure you're checking HTTP status codes, not curl exit codes:
```bash
# WRONG - checks curl exit code (always 0 if server responds)
curl -s http://127.0.0.1:8003/api/ > /dev/null && echo "SUCCESS"

# RIGHT - checks HTTP status code
if [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8003/api/)" = "200" ]; then
  echo "SUCCESS"
fi
```

### Container logs:

```bash
docker compose logs -f web
```

### Database connection errors:

```bash
docker compose exec db pg_isready -U postgres
```

### Restart containers:

```bash
docker compose restart web
```

---

## Related Projects

- **proj01_add_not_null_constraint** - Shows risky NOT NULL constraint addition
- **proj01_safe_backfill** - Shows safe NOT NULL constraint with batching
- **proj04_change_column_type** - Shows risky column type change
- **proj04_safe_backfill** - Shows safe column type change with add-copy-swap pattern

See the main `CLAUDE.md` for all 10 risky migration scenarios.

---

## Next Steps

After this demo, explore:
- How to audit your codebase for column references before dropping
- Using database views to maintain backward compatibility during transitions
- Setting up alerts for FieldError exceptions in production
- Creating a "deprecated columns" policy for your team
