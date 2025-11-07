# Demo Commands for proj04_safe_backfill

This file contains step-by-step commands to demonstrate the SAFE way to change column types on large tables using the add-new-column + backfill + enforce pattern.

## Prerequisites

Ensure Docker and Docker Compose are installed on your system.

---

## Overview

This project demonstrates the **safe 3-step pattern** for changing column types:

1. **Migration 0002**: Add new nullable `created_at_new` DateTimeField (instant)
2. **Migration 0003**: Backfill data from `created_at` to `created_at_new` in batches (safe, no blocking)
3. **Migration 0004**: Enforce NOT NULL on `created_at_new` (instant)

Compare this to `proj04_change_column_type` which shows the risky direct column type change.

---

## Step 1: Start the Containers

```bash
cd proj04_safe_backfill
docker compose up --build -d
```

This will:
- Start PostgreSQL 16 database on port 5434
- Build and start Django application
- Start Django dev server on http://localhost:8002

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
 [ ] 0002_largerecord_created_at_new_and_more
 [ ] 0003_backfill_created_at_new
 [ ] 0004_alter_largerecord_created_at_new_and_more
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
docker compose exec db psql -U postgres -d risky_migrations -c "SELECT COUNT(*) FROM large_record;"
```

Expected output:
```
  count
----------
 10000000
```

---

## Step 4: Test the Endpoint (Before Migrations)

```bash
curl http://127.0.0.1:8002/list_large/
```

Expected response (fast, < 1 second):
```json
{
  "records": [
    {"id": 1, "name": "LargeRecord_1", "created_at": "2024-01-01 10:00:00"},
    ...
  ],
  "count": 10
}
```

---

## Step 5: Migration 0002 - Add New Nullable Column (INSTANT)

**What it does:** Adds `created_at_new` as a nullable DateTimeField

```bash
docker compose exec web python manage.py migrate demoapp 0002
```

**Observation:** This completes **instantly** (< 1 second) regardless of table size!

Why it's fast:
- Adding a nullable column requires no data validation
- No table rewrite needed
- No locks on existing data

Check the table structure:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_record"
```

You'll see both columns:
```
                         Table "public.large_record"
     Column      |          Type          | Collation | Nullable | Default
-----------------+------------------------+-----------+----------+---------
 id              | bigint                 |           | not null |
 name            | character varying(100) |           | not null |
 created_at      | character varying(50)  |           | not null |   <-- Old column (string)
 created_at_new  | timestamp              |           |          |   <-- New column (nullable)
```

---

## Step 6: Migration 0003 - Backfill Data in Batches (SAFE, NO BLOCKING)

**What it does:** Copies data from `created_at` to `created_at_new` using raw SQL in 10K row batches

### Terminal 1 - Run the backfill migration:

```bash
docker compose exec web python manage.py migrate demoapp 0003
```

### Terminal 2 - Test API during backfill (remains responsive!):

```bash
while true; do
  echo "[$(date +%H:%M:%S)] Request";
  curl -s --max-time 3 http://127.0.0.1:8002/list_large/ > /dev/null && echo " ✅ SUCCESS" || echo " ❌ BLOCKED";
  sleep 0.5;
done
```

### What You'll Observe:

**Terminal 1** - Fast backfill progress:
```
[15:20:00] Starting batch backfill for LargeRecord...
[15:20:05] Batch 10: Updated 10,000 rows in 0.45s (Total: 100,000)
[15:20:10] Batch 20: Updated 10,000 rows in 0.42s (Total: 200,000)
[15:20:14] Batch 30: Updated 10,000 rows in 0.41s (Total: 300,000)
...
[15:28:20] LargeRecord backfill complete! Total: 10,000,000 rows
```

**Terminal 2** - API remains fully responsive:
```
[15:20:01] Request
 ✅ SUCCESS
[15:20:02] Request
 ✅ SUCCESS
[15:20:03] Request
 ✅ SUCCESS
```

**Performance:**
- ~0.4 seconds per 10K rows batch (optimized with raw SQL)
- ~8-10 minutes for 10M rows
- **Zero downtime** - API works throughout!

Verify backfill completion:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT COUNT(*) as total_rows,
       COUNT(created_at_new) as backfilled_rows
FROM large_record;
"
```

Expected output:
```
 total_rows | backfilled_rows
------------+-----------------
   10000000 |        10000000
```

---

## Step 7: Migration 0004 - Enforce NOT NULL (INSTANT)

**What it does:** Makes `created_at_new` NOT NULL after all data is backfilled

```bash
docker compose exec web python manage.py migrate demoapp 0004
```

**Observation:** This completes **instantly** (< 1 second)!

Why it's fast:
- All rows already have values (thanks to migration 0003)
- PostgreSQL doesn't need to scan the table
- Just updating the column metadata

Check final table structure:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_record"
```

You'll see:
```
                         Table "public.large_record"
     Column      |          Type          | Collation | Nullable | Default
-----------------+------------------------+-----------+----------+---------
 id              | bigint                 |           | not null |
 name            | character varying(100) |           | not null |
 created_at      | character varying(50)  |           | not null |   <-- Old column
 created_at_new  | timestamp              |           | not null |   <-- New column (now NOT NULL!)
```

---

## Step 8: Compare Performance - Safe vs Risky

### Safe Way (Migrations 0002, 0003, 0004):

```bash
# Start from 0001
docker compose exec web python manage.py migrate demoapp 0001

# Run all three safe migrations
time docker compose exec web python manage.py migrate demoapp 0002  # < 1 second
time docker compose exec web python manage.py migrate demoapp 0003  # 8-10 minutes, batched
time docker compose exec web python manage.py migrate demoapp 0004  # < 1 second
```

**Result:**
- ✅ Step 0002: Instant (add nullable column)
- ✅ Step 0003: 8-10 minutes (batched backfill, API responsive)
- ✅ Step 0004: Instant (enforce NOT NULL)
- ✅ **ZERO downtime** - API works throughout
- ✅ Safe rollback at each step
- ✅ Total time: ~8-10 minutes

### Risky Way (shown in proj04_change_column_type):

Direct column type change would:
- ❌ Take 30-60 seconds for 10M rows
- ❌ **Complete downtime** - all queries blocked
- ❌ Risk of data loss if conversion fails
- ❌ Cannot rollback safely mid-migration

---

## Step 9: Timeline Visualization

### Safe Approach (0002 + 0003 + 0004):
```
0:00 [0002: instant] ─────[0003: 8min batched]───── [0004: instant] 8:00
       ✅ API responsive throughout entire process
       ✅ Short locks per batch (0.4s per 10K rows)
       ✅ Can monitor progress in real-time
```

### Risky Approach (direct column type change):
```
0:00 ────────────[DOWNTIME: 30-60 seconds]──────────── 1:00
       ❌ API completely blocked
       ❌ All queries timeout
       ❌ No progress visibility
```

---

## Step 10: Advanced - Monitor Backfill in Real-Time

### Check backfill progress while running:

```bash
# Terminal 1 - Run migration
docker compose exec web python manage.py migrate demoapp 0003

# Terminal 2 - Monitor progress
watch -n 1 "docker compose exec db psql -U postgres -d risky_migrations -c \"
SELECT COUNT(*) as total,
       COUNT(created_at_new) as backfilled,
       ROUND(100.0 * COUNT(created_at_new) / COUNT(*), 2) as percent_done
FROM large_record;
\""
```

Expected output (updates every second):
```
  total   | backfilled | percent_done
----------+------------+--------------
 10000000 |    1500000 |        15.00
```

### Monitor active queries during backfill:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT pid, usename, state, query_start, query
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state != 'idle'
ORDER BY query_start;
"
```

---

## Additional Commands

### Check table sizes:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('small_record', 'large_record');
"
```

### Check row counts at each stage:

```bash
# After 0001: Only created_at exists
docker compose exec db psql -U postgres -d risky_migrations -c "SELECT COUNT(*) FROM large_record;"

# After 0002: created_at_new exists but is NULL
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT COUNT(*) as total, COUNT(created_at_new) as backfilled FROM large_record;
"

# After 0003: All rows backfilled
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT COUNT(*) as total, COUNT(created_at_new) as backfilled FROM large_record;
"
```

### Sample data inspection:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT id, name, created_at, created_at_new
FROM large_record
LIMIT 5;
"
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

### ✅ Safe Column Type Change Pattern (3 Steps)

**Step 1 (Migration 0002): Add nullable column**
- Add `created_at_new` as DateTimeField(null=True)
- Instant operation (< 1 second)
- No data validation needed
- No locks on existing data

**Step 2 (Migration 0003): Backfill in batches**
- Copy data using raw SQL: `UPDATE ... SET created_at_new = created_at::timestamp`
- Process 10,000 rows per batch
- Each batch takes ~0.4 seconds
- Total time: ~8-10 minutes for 10M rows
- **Zero downtime** - API remains responsive
- Progress tracking every 10 batches

**Step 3 (Migration 0004): Enforce NOT NULL**
- Change to `DateTimeField(default=timezone.now)`
- Instant operation (< 1 second)
- No table scan needed (data already populated)

### 📊 Performance Comparison

| Metric | Risky Direct Change | Safe 3-Step Pattern |
|--------|---------------------|---------------------|
| Total Time (10M rows) | 30-60 seconds | 8-10 minutes |
| API Downtime | 30-60 seconds | **0 seconds** |
| Lock Duration | Full table lock | 0.4s per 10K rows |
| Rollback Safety | Risky | Safe at each step |
| Progress Visibility | None | Real-time tracking |
| Memory Usage | High | Low (batch processing) |
| Production Ready | ❌ No | ✅ Yes |

### 🎯 When to Use This Pattern

**Always use the safe pattern when:**
- Table has 100,000+ rows
- Zero downtime is required
- Production environment
- High-traffic applications
- Need to monitor progress
- Want safe rollback capability

**Only use direct change when:**
- Table has < 10,000 rows
- Downtime is acceptable
- Non-production environment
- Emergency fixes only

---

## Optimization Notes

### Why Raw SQL is Used (Migration 0003)

The backfill migration uses raw SQL instead of Django ORM because:

**Original ORM Approach (SLOW - 5s per batch):**
```python
records = list(LargeRecord.objects.filter(id__in=ids_to_update))
for record in records:
    record.created_at_new = timezone.make_aware(
        datetime.strptime(record.created_at, '%Y-%m-%d %H:%M:%S')
    )
LargeRecord.objects.bulk_update(records, ['created_at_new'])
```
- Loads 10K objects into Python memory
- Loops through each in Python
- Serializes back to database
- Result: ~5 seconds per 10K rows (83 minutes for 10M rows!)

**Optimized Raw SQL (FAST - 0.4s per batch):**
```python
cursor.execute("""
    UPDATE large_record
    SET created_at_new = created_at::timestamp
    WHERE id IN (
        SELECT id FROM large_record
        WHERE created_at_new IS NULL
        LIMIT %s
    )
""", [batch_size])
```
- All processing done in PostgreSQL
- No Python loops
- Direct type casting in database
- Result: ~0.4 seconds per 10K rows (8 minutes for 10M rows!)

**Performance Gain: 12.5x faster!**

---

## Troubleshooting

### Backfill seems stuck:

Check if it's actually progressing:
```bash
docker compose logs -f web
```

### Database connection errors:

```bash
docker compose exec db pg_isready -U postgres
```

### Container logs:

```bash
docker compose logs -f web
docker compose logs -f db
```

### Restart containers:

```bash
docker compose restart web
```

### Out of memory:

Reduce batch size further:
```python
# In 0003_backfill_created_at_new.py
batch_size = 5000  # Instead of 10000
```

---

## Related Projects

- **proj04_change_column_type** - Shows the RISKY direct column type change (for comparison)
- **proj01_add_not_null_constraint** - Similar pattern for adding NOT NULL constraints
- **proj01_safe_backfill** - Shows safe batched data backfill patterns

See the main `CLAUDE.md` for all 10 risky migration scenarios.

---

## Next Steps (TODO)

After migration 0004, you would typically:

5. **Update application code** to use `created_at_new` instead of `created_at`
6. **Deploy code changes**
7. **Migration 0005**: Drop old `created_at` column
8. **Migration 0006**: Rename `created_at_new` to `created_at` (optional)

This completes the zero-downtime column type change!
