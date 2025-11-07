# Demo Commands for proj01_add_not_null_constraint

This file contains step-by-step commands to demonstrate the risks of adding a NOT NULL constraint to a large table.

## Setup (Already Done)

```bash
cd proj01_add_not_null_constraint
docker compose up -d
docker compose exec web python manage.py seed_large_table --large-count 1000000
```

## Current State

- Migration: `0001_initial` (tables with only `id` and `name` fields)
- Data: 10 rows in small_user, 1M rows in large_user
- Models: status field is commented out

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
 [ ] 0003_alter_largeuser_status_alter_smalluser_status
```

**Test API (should work fast):**
```bash
curl http://127.0.0.1:8000/list_large/
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

## Step 2: Add Nullable Status Field (Migration 0002)

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

**Observation:** This is FAST! Adding a nullable column doesn't require validating existing rows.

**Verify column was added:**
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_user"
```

**Test API (still works):**
```bash
curl http://127.0.0.1:8000/list_large/
```

---

## Step 3: Demonstrate the Risky Migration (0003 - Add NOT NULL Constraint)

### Terminal 1: Start monitoring API requests

Run this in a loop to continuously query the API:
```bash
while true; do
  echo -n "$(date +%H:%M:%S) - "
  curl --max-time 3 http://127.0.0.1:8000/list_large/ 2>&1 | grep -q "users" && echo "✓ API responded" || echo "✗ API blocked/timeout"
  sleep 1
done
```

### Terminal 2: Run the risky migration

```bash
docker compose exec web python manage.py migrate demoapp 0003
```

### What You'll Observe:

- **Terminal 2:** Migration takes several seconds (validating 1M rows)
- **Terminal 1:** API requests **BLOCK** during migration - you'll see timeout messages
- **After migration completes:** API requests resume working

---

## Step 4: Understand What Happened

**Check migration status:**
```bash
docker compose exec web python manage.py showmigrations demoapp
```

All migrations should now be applied:
```
demoapp
 [X] 0001_initial
 [X] 0002_largeuser_status_smalluser_status
 [X] 0003_alter_largeuser_status_alter_smalluser_status
```

**Explain the problem:**

Migration 0003 added a NOT NULL constraint on the status field. PostgreSQL had to:

1. **Scan all 1,000,000 rows** to verify no NULLs exist
2. **Hold a table-level ACCESS EXCLUSIVE lock** during validation
3. **Block ALL queries** (even simple SELECTs) until complete

**Result:** API downtime for the entire migration duration (several seconds for 1M rows, could be minutes/hours for 100M+ rows)

---

## Step 5: Rollback and Show the Safe Approach

**Rollback to migration 0001:**
```bash
docker compose exec web python manage.py migrate demoapp 0001
```

**Comment out status field again:**
```bash
docker compose exec web sed -i 's/status = models/# status = models/g' demoapp/models.py
```

**Explain the safe alternative:**

The SAFE way (demonstrated in `proj01_safe_backfill`):

1. **Add nullable column** (fast, no validation)
   ```python
   status = models.CharField(max_length=20, null=True, blank=True)
   ```

2. **Backfill data in small batches** (10k-100k rows at a time)
   ```python
   # Data migration with batching
   batch_size = 10000
   while exists_null_status:
       update_batch(batch_size)  # Short transaction
       commit()  # Release locks
   ```

3. **Add NOT NULL constraint** (fast, all rows have values)
   ```python
   status = models.CharField(max_length=20, default='active')
   ```

**Total time is similar, but ZERO downtime!** API remains responsive during step 2.

---

## Bonus: Visual Comparison

**Show table structure at each stage:**

### After 0001:
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_user"
```
Fields: `id`, `name`

### After 0002:
```bash
docker compose exec web python manage.py migrate demoapp 0002
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_user"
```
Fields: `id`, `name`, `status` (nullable)

### After 0003:
```bash
docker compose exec web python manage.py migrate demoapp 0003
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_user"
```
Fields: `id`, `name`, `status` (NOT NULL with default)

---

## Advanced: Check Locks During Migration

**Terminal 1: Monitor locks**
```bash
while true; do
  docker compose exec db psql -U postgres -d risky_migrations -c "SELECT pid, usename, state, query, wait_event_type FROM pg_stat_activity WHERE datname = 'risky_migrations' AND query NOT LIKE '%pg_stat_activity%';"
  sleep 1
done
```

**Terminal 2: Run migration**
```bash
docker compose exec web python manage.py migrate demoapp 0003
```

You'll see the migration holding an `ACCESS EXCLUSIVE` lock and other queries waiting.

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

### ❌ Wrong Way (Migration 0003)
- Direct `null=True → null=False` change
- Full table scan with exclusive lock
- Blocks all queries for entire duration
- Production downtime

### ✅ Right Way (See proj01_safe_backfill)
- Step 1: Add nullable column (instant)
- Step 2: Backfill in batches (safe, responsive)
- Step 3: Add NOT NULL (instant, already populated)
- Zero downtime

---

## Related Projects

- **proj01_safe_backfill** - Demonstrates the safe batched approach
- See the main `CLAUDE.md` for all 10 risky migration scenarios
