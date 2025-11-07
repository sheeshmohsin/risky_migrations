# Demo Commands for proj04_change_column_type

This file contains step-by-step commands to demonstrate the risks of changing column types on large tables and the safe alternative approach.

## Prerequisites

Ensure Docker and Docker Compose are installed on your system.

---

## Step 1: Start the Containers

```bash
cd proj04_change_column_type
docker compose up --build -d
```

This will:
- Start PostgreSQL 16 database
- Build and start Django application
- Run initial migrations (0001_initial through 0005)
- Start Django dev server on http://localhost:8002

---

## Step 2: Reset to Initial State

Since containers start with all migrations applied, let's reset to the beginning:

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
 [ ] 0002_alter_largerecord_created_at_and_more
 [ ] 0003_largerecord_created_at_new_and_more
 [ ] 0004_backfill_created_at_new
 [ ] 0005_alter_largerecord_created_at_new_and_more
```

---

## Step 3: Seed the Database

Seed with 10 million rows for a realistic demonstration:

```bash
docker compose exec web python manage.py seed_large_table --large-count 10000000
```

For faster testing (1 million rows):

```bash
docker compose exec web python manage.py seed_large_table --large-count 1000000
```

**Note:** The seed command now uses a batch size of 10,000 rows by default (optimized to prevent database crashes).

Verify the data:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "SELECT COUNT(*) FROM large_record;"
```

---

## Step 4: Test the Endpoint (Before Migration)

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

## Step 5: Demonstrate the RISKY Migration (0002 - Direct Column Type Change)

### What Migration 0002 Does:
Changes `created_at` field from `CharField` (VARCHAR) to `DateTimeField` (TIMESTAMP) **directly**.

This causes PostgreSQL to:
1. Rewrite the entire table
2. Hold an ACCESS EXCLUSIVE lock
3. Block ALL reads and writes
4. Take a very long time on large tables

### Option A: Three Terminal Demonstration

**Terminal 1** - Server is already running via docker-compose

**Terminal 2** - Continuous API requests:
```bash
while true; do
  echo "[$(date +%H:%M:%S)] Request";
  curl -s --max-time 3 http://127.0.0.1:8002/list_large/ > /dev/null && echo " ✅ SUCCESS" || echo " ❌ BLOCKED/TIMEOUT";
  sleep 0.5;
done
```

**Terminal 3** - Run the risky migration:
```bash
docker compose exec web python manage.py migrate demoapp 0002
```

**What you'll observe:**
- Terminal 2 shows continuous SUCCESS messages before migration
- Once Terminal 3 starts the migration, Terminal 2 shows BLOCKED/TIMEOUT
- Blocking lasts for the entire duration of the column type change (30-60 seconds with 10M rows)
- After migration completes, Terminal 2 returns to SUCCESS messages

### Option B: Automated Single-Command Demonstration

```bash
(for i in {1..120}; do
  echo "[$(date +%H:%M:%S)] Request $i";
  curl -s --max-time 3 http://127.0.0.1:8002/list_large/ > /dev/null && echo " ✅ SUCCESS" || echo " ❌ BLOCKED/TIMEOUT";
  sleep 0.5;
done) &
sleep 2 &&
echo "🚀 STARTING RISKY MIGRATION (0002)..." &&
docker compose exec -T web python manage.py migrate demoapp 0002 &&
echo "✅ MIGRATION COMPLETE" &&
wait
```

---

## Step 6: Understand What Happened

Check the migration timing:

```bash
docker compose logs web | grep -A 30 "Starting migration"
```

You'll see output like:
```
============================================================
[2025-11-07 19:10:00] Starting migration: Changing column type
============================================================

[2025-11-07 19:10:00.123] Changing SmallRecord.created_at from VARCHAR to DATETIME...
[2025-11-07 19:10:00.145] ✓ SmallRecord column type changed

[2025-11-07 19:10:00.150] Changing LargeRecord.created_at from VARCHAR to DATETIME...
[2025-11-07 19:10:45.892] ✓ LargeRecord column type changed   <-- 45 seconds of downtime!

============================================================
[2025-11-07 19:10:45] Migration completed
============================================================
```

**Why this is dangerous:**
- PostgreSQL rewrites the entire table to convert data types
- Holds ACCESS EXCLUSIVE lock (blocks ALL operations)
- 45 seconds of complete downtime for 10M rows
- Could be **hours** for 100M+ row tables in production
- Risk of data loss if conversion fails

---

## Step 7: Rollback and Demonstrate the SAFE Approach

### Rollback to 0001:

```bash
docker compose exec web python manage.py migrate demoapp 0001
```

---

## Step 8: The Safe Way - Migration 0003 (Add New Column)

**What it does:** Adds a new `created_at_new` column as DateTimeField (nullable)

```bash
docker compose exec web python manage.py migrate demoapp 0003
```

**Observation:** This is **INSTANT** - just adds a nullable column, no data manipulation!

Check the table structure:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_record"
```

You'll see both columns:
- `created_at` (character varying) - old column
- `created_at_new` (timestamp without time zone) - new column (nullable)

---

## Step 9: The Safe Way - Migration 0004 (Backfill in Batches)

**What it does:** Copies data from `created_at` to `created_at_new` in batches of 100,000 rows

### Terminal 1 - Run the backfill migration:

```bash
docker compose exec web python manage.py migrate demoapp 0004
```

### Terminal 2 - Test API during backfill:

```bash
while true; do
  echo "[$(date +%H:%M:%S)] Request";
  curl -s --max-time 3 http://127.0.0.1:8002/list_large/ > /dev/null && echo " ✅ SUCCESS" || echo " ❌ BLOCKED";
  sleep 0.5;
done
```

**Observation:**
- API remains **fully responsive** during backfill!
- Each batch takes a short time (< 1 second)
- Locks are held briefly and released between batches
- Total time similar to risky approach, but **ZERO downtime**

Watch the progress:

```bash
docker compose logs -f web
```

You'll see output like:
```
[19:15:00] Batch 1 backfilled: 100,000 rows (0.8s)
[19:15:01] Batch 2 backfilled: 100,000 rows (0.7s)
[19:15:02] Batch 3 backfilled: 100,000 rows (0.8s)
...
[19:16:20] Backfill complete! Total: 10,000,000 rows
```

---

## Step 10: The Safe Way - Migration 0005 (Enforce NOT NULL)

**What it does:** Makes `created_at_new` NOT NULL after all data is backfilled

```bash
docker compose exec web python manage.py migrate demoapp 0005
```

**Observation:** This is **INSTANT** - all rows already have values, just enforcing the constraint!

Check final table structure:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_record"
```

---

## Step 11: Compare Both Approaches

### Risky Way (Migration 0002):
```bash
# Start from 0001
docker compose exec web python manage.py migrate demoapp 0001

# Run risky migration
time docker compose exec web python manage.py migrate demoapp 0002
```

**Result:**
- ❌ Single migration: 30-60 seconds
- ❌ Complete downtime during entire migration
- ❌ All queries blocked
- ❌ Risk of data loss if conversion fails

### Safe Way (Migrations 0003, 0004, 0005):
```bash
# Start from 0001
docker compose exec web python manage.py migrate demoapp 0001

# Run safe migrations
time docker compose exec web python manage.py migrate demoapp 0003  # Instant
time docker compose exec web python manage.py migrate demoapp 0004  # 30-60 seconds, batched
time docker compose exec web python manage.py migrate demoapp 0005  # Instant
```

**Result:**
- ✅ Step 0003: Instant (add nullable column)
- ✅ Step 0004: 30-60 seconds (batched backfill, API responsive)
- ✅ Step 0005: Instant (enforce NOT NULL)
- ✅ **ZERO downtime** - API works throughout
- ✅ Safe rollback at each step
- ✅ No risk of data loss

---

## Step 12: Visual Comparison

### Migration Timeline Visualization:

**Risky Approach (0002):**
```
0:00 ──────────[DOWNTIME: 60 seconds]────────── 1:00
       ❌ API blocked entire time
```

**Safe Approach (0003 + 0004 + 0005):**
```
0:00 [0003: instant] ─[0004: 60s batched]─ [0005: instant] 1:00
       ✅ API responsive throughout
```

---

## Additional Commands

### Check table sizes:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('small_record', 'large_record');
"
```

### Monitor active queries during migration:

```bash
# Run this in another terminal while migration is running
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT pid, usename, state, query, wait_event_type
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state != 'idle';
"
```

### Check for blocked queries:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query,
       blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.granted
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
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

### ❌ Wrong Way (Direct Column Type Change - Migration 0002)
- Single `AlterField` operation
- Rewrites entire table with full table lock
- Blocks ALL queries (reads AND writes)
- 30-60 seconds of complete downtime on 10M rows
- Hours of downtime on 100M+ rows
- Risk of data loss if conversion fails

### ✅ Right Way (New Column + Batched Copy + Swap - Migrations 0003, 0004, 0005)
- **Migration 0003**: Add nullable `created_at_new` column (instant)
- **Migration 0004**: Backfill in 100k row batches (safe, short locks)
- **Migration 0005**: Enforce NOT NULL constraint (instant)
- **Zero downtime** - API remains fully responsive
- Can rollback at each step
- No data loss risk

### When to Use Each Approach:

**Direct column type change (risky) is acceptable when:**
- Table has < 10,000 rows
- Downtime is acceptable
- Non-production environment

**Safe batched approach is required when:**
- Table has 100,000+ rows
- Zero downtime is needed
- Production environment
- High-traffic applications

---

## Troubleshooting

### Database connection errors during seeding:

If you see "server closed the connection unexpectedly" errors, the default batch size has been reduced to 10,000. The seed command should now work reliably.

### Container logs:

```bash
docker compose logs -f web
docker compose logs -f db
```

### Database not ready:

```bash
docker compose exec db pg_isready -U postgres
```

### Restart containers:

```bash
docker compose restart web
```

---

## Related Projects

- **proj01_add_not_null_constraint** - Demonstrates adding NOT NULL constraints safely
- **proj01_safe_backfill** - Shows safe batched data backfill patterns
- **proj03_indexes** - Demonstrates index creation blocking
- **proj03_safe_backfill** - Shows CREATE INDEX CONCURRENTLY approach

See the main `CLAUDE.md` for all 10 risky migration scenarios.
