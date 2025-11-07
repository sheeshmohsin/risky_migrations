# Demo Commands for proj01_safe_backfill

This file contains step-by-step commands to demonstrate the SAFE way to add a NOT NULL constraint using batched backfilling.

## Setup (Already Done)

```bash
cd proj01_safe_backfill
docker compose up -d --build
docker compose exec web python manage.py seed_large_table --large-count 1000000
```

## Current State

- Migration: `0001_initial` (tables with only `id` and `name` fields)
- Data: 10 rows in small_user, 1M rows in large_user
- Models: status field is commented out
- **Port**: This project runs on **8001** (not 8000)

---

## Step 1: Verify Current State

**Check migrations:**
```bash
docker compose exec web python manage.py showmigrations demoapp
```

Expected output:
```
demoapp
 [X] 0001_initial
 [ ] 0002_largeuser_status_smalluser_status
 [ ] 0003_backfill_status_field
 [ ] 0004_alter_largeuser_status_alter_smalluser_status
```

**Test API (should work fast on port 8001):**
```bash
curl http://127.0.0.1:8001/list_large/
```

**Check row counts:**
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "SELECT 'small_user' as table, COUNT(*) FROM small_user UNION ALL SELECT 'large_user', COUNT(*) FROM large_user;"
```

Expected output:
```
    table    |  count
-------------+---------
 small_user  |      10
 large_user  | 1000000
```

---

## Step 2: Add Nullable Status Field (Migration 0002) - SAFE & FAST

**Uncomment status field in models.py:**
```bash
# Edit demoapp/models.py and uncomment these lines in both SmallUser and LargeUser:
# status = models.CharField(max_length=20, null=True, blank=True)
```

Or use this command:
```bash
docker compose exec web sed -i 's/# status = models/status = models/g' demoapp/models.py
```

**Run migration 0002:**
```bash
docker compose exec web python manage.py migrate demoapp 0002
```

**Observation:** This is **INSTANT!** Adding a nullable column is just a metadata change - no table scan, no locks.

**Verify column was added:**
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_user"
```

You should see the `status` column with `| character varying(20) |` and allowing NULLs.

**Test API (still fast, data still has NULL status):**
```bash
curl http://127.0.0.1:8001/list_large/
```

---

## Step 3: Backfill in Batches (Migration 0003) - SAFE & RESPONSIVE

This is the **KEY MIGRATION** that makes the approach safe!

### Terminal 1: Monitor API responsiveness

Run this loop to continuously query the API while backfill runs:
```bash
while true; do
  echo -n "$(date +%H:%M:%S) - "
  curl --max-time 3 http://127.0.0.1:8001/list_large/ 2>&1 | grep -q "users" && echo "✓ API responded" || echo "✗ API blocked/timeout"
  sleep 1
done
```

### Terminal 2: Run the batch backfill migration

```bash
docker compose exec web python manage.py migrate demoapp 0003
```

### What You'll Observe:

**Terminal 2 - Migration output:**
```
Starting backfill for SmallUser...
Backfilled 10 SmallUser rows

Starting batch backfill for LargeUser...
Batch size: 10,000 rows
[HH:MM:SS] Batch 10: Updated 10,000 rows in 0.15s. Total: 100,000 rows
[HH:MM:SS] Batch 20: Updated 10,000 rows in 0.14s. Total: 200,000 rows
...
Backfill complete!
Total LargeUser rows backfilled: 1,000,000
Total batches: 100
```

**Terminal 1 - API monitoring:**
```
22:30:15 - ✓ API responded
22:30:16 - ✓ API responded
22:30:17 - ✓ API responded
22:30:18 - ✓ API responded
...continues responding throughout the entire backfill!
```

**Key Points:**
- ✅ Each batch updates only 10,000 rows (~0.1-0.2 seconds)
- ✅ Transaction commits after each batch, releasing locks
- ✅ Other queries can run between batches
- ✅ **API remains responsive the entire time!**
- ✅ Total time: ~10-20 seconds for 1M rows

**Verify backfill completed:**
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "SELECT COUNT(*) as total_rows, COUNT(status) as rows_with_status, COUNT(*) - COUNT(status) as rows_null FROM large_user;"
```

Should show all rows have status values:
```
 total_rows | rows_with_status | rows_null
------------+------------------+-----------
    1000000 |          1000000 |         0
```

---

## Step 4: Add NOT NULL Constraint (Migration 0004) - SAFE & INSTANT

Now that all rows have values, adding the NOT NULL constraint is instant!

**Run migration 0004:**
```bash
docker compose exec web python manage.py migrate demoapp 0004
```

**Observation:** This is **INSTANT!** PostgreSQL can see all rows already have values, so no validation scan is needed.

**Verify constraint was added:**
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_user"
```

The `status` column should now show `NOT NULL` constraint.

**Test API (still fast):**
```bash
curl http://127.0.0.1:8001/list_large/
```

---

## Step 5: Understanding the Safe Approach

**Check all migrations are applied:**
```bash
docker compose exec web python manage.py showmigrations demoapp
```

Should show:
```
demoapp
 [X] 0001_initial
 [X] 0002_largeuser_status_smalluser_status
 [X] 0003_backfill_status_field
 [X] 0004_alter_largeuser_status_alter_smalluser_status
```

### Why This Approach Works:

**Step 1 (0002): Add Nullable Column**
- Duration: Instant (< 0.1 seconds)
- Lock: None (metadata only)
- Impact: Zero

**Step 2 (0003): Batch Backfill**
- Duration: ~10-20 seconds for 1M rows
- Lock: Short locks per batch (~0.15s each)
- Impact: Minimal - queries can run between batches
- **Key**: Each transaction is < 1 second

**Step 3 (0004): Add NOT NULL**
- Duration: Instant (< 0.1 seconds)
- Lock: None (all rows validated)
- Impact: Zero

**Total**: ~20 seconds with **ZERO downtime!**

---

## Compare with Risky Approach (proj01_add_not_null_constraint)

### Risky Way (Direct NOT NULL):
```
❌ Single migration: null=True → null=False
❌ Full table scan to validate
❌ Table locked for entire duration (10-30 seconds for 1M rows)
❌ All queries blocked
❌ Production downtime
```

### Safe Way (This Project):
```
✅ Three-step migration
✅ Step 1: Add nullable (instant)
✅ Step 2: Backfill in batches (short locks)
✅ Step 3: Add NOT NULL (instant)
✅ API responsive throughout
✅ Zero downtime
```

---

## Bonus: Monitor Batch Progress in Real-Time

### Terminal 1: Watch backfill progress
```bash
docker compose exec web python manage.py migrate demoapp 0003
```

### Terminal 2: Monitor database activity
```bash
while true; do
  echo "=== $(date +%H:%M:%S) ==="
  docker compose exec db psql -U postgres -d risky_migrations -c "SELECT COUNT(*) as total, COUNT(status) as backfilled, COUNT(*) - COUNT(status) as remaining FROM large_user;"
  sleep 2
done
```

You'll see the `remaining` count decrease in real-time as batches complete!

---

## Bonus: Check Locks During Backfill

Run this BEFORE starting migration 0003:

**Terminal 1: Monitor locks**
```bash
while true; do
  echo "=== $(date +%H:%M:%S) ==="
  docker compose exec db psql -U postgres -d risky_migrations -c "SELECT pid, usename, state, wait_event_type, LEFT(query, 50) as query FROM pg_stat_activity WHERE datname = 'risky_migrations' AND query NOT LIKE '%pg_stat_activity%';"
  sleep 1
done
```

**Terminal 2: Run backfill**
```bash
docker compose exec web python manage.py migrate demoapp 0003
```

**Observation:** You'll see brief locks during each batch update, but they only last a fraction of a second!

---

## Rollback and Replay

**Rollback to start (removes status field):**
```bash
docker compose exec web python manage.py migrate demoapp 0001
docker compose exec web sed -i 's/status = models/# status = models/g' demoapp/models.py
```

**Replay the safe migration:**
```bash
# Step 1: Add nullable
docker compose exec web sed -i 's/# status = models/status = models/g' demoapp/models.py
docker compose exec web python manage.py migrate demoapp 0002

# Step 2: Backfill (watch it work!)
docker compose exec web python manage.py migrate demoapp 0003

# Step 3: Add NOT NULL
docker compose exec web python manage.py migrate demoapp 0004
```

---

## Advanced: Batch Size Impact

The migration uses `batch_size = 10000`. You can experiment with different batch sizes:

**Edit the migration file:**
```bash
docker compose exec web nano demoapp/migrations/0003_backfill_status_field.py
# Change: batch_size = 10000
# To: batch_size = 1000 (slower but more responsive)
# Or: batch_size = 100000 (faster but longer locks)
```

**Recommended batch sizes:**
- **1,000-5,000**: Maximum responsiveness, longer total time
- **10,000-50,000**: Good balance (recommended)
- **100,000+**: Faster but may cause noticeable delays

---

## Cleanup

**Stop containers:**
```bash
docker compose down
```

**Stop and remove data (deletes database):**
```bash
docker compose down -v
```

**Restart fresh:**
```bash
docker compose up -d --build
docker compose exec web python manage.py seed_large_table --large-count 1000000
```

---

## Key Takeaways

### ❌ Risky Approach (proj01_add_not_null_constraint)
- Direct `null=True → null=False`
- Full table scan with exclusive lock
- Blocks all queries for 10-30+ seconds
- Production downtime

### ✅ Safe Approach (This Project)
- **Step 1**: Add nullable column (instant, no lock)
- **Step 2**: Backfill in batches (short locks, API responsive)
- **Step 3**: Add NOT NULL (instant, already validated)
- **Zero downtime**, production-safe

### The Secret: Batching

```python
# Instead of this (risky - locks entire table):
LargeUser.objects.all().update(status='active')

# Do this (safe - short locks per batch):
batch_size = 10000
while LargeUser.objects.filter(status__isnull=True).exists():
    ids = list(LargeUser.objects.filter(status__isnull=True)
               .values_list('id', flat=True)[:batch_size])
    LargeUser.objects.filter(id__in=ids).update(status='active')
    # Transaction commits here, releasing locks!
```

---

## Related Projects

- **proj01_add_not_null_constraint** - Shows the RISKY direct approach
- **This project** - Shows the SAFE batched approach
- See the main `CLAUDE.md` for all 10 risky migration scenarios
