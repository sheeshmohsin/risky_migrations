# proj03_indexes - Demo Commands

This file contains the exact commands needed to demonstrate how index creation on large tables blocks write operations, causing API failures and timeouts in production.

## Prerequisites

Ensure Docker and Docker Compose are installed on your system.

## Step 1: Start the Containers

```bash
cd proj03_indexes
docker compose up --build -d
```

This will:
- Start PostgreSQL 16 database
- Build and start Django application
- Run initial migrations
- Start Django dev server on http://localhost:8000

## Step 2: Seed the Database

For a meaningful demonstration with ~35 second migration time:

```bash
# Seed with 10 million rows (takes ~2-3 minutes)
docker compose exec web python manage.py seed_large_table --large-count 10000000 --batch-size 10000
```

For faster testing (shorter migration time):

```bash
# Seed with 1 million rows (takes ~15 seconds, migration ~5 seconds)
docker compose exec web python manage.py seed_large_table --large-count 1000000 --batch-size 10000
```

Verify the data:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "SELECT COUNT(*) FROM large_email;"
```

## Step 3: Reset Migration to Pre-Index State

```bash
docker compose exec web python manage.py migrate demoapp 0001
```

Check migration status:

```bash
docker compose exec web python manage.py showmigrations demoapp
```

You should see:
```
demoapp
 [X] 0001_initial
 [ ] 0002_alter_largeemail_email_alter_smallemail_email
```

## Step 4: Test the Endpoint (Before Migration)

The `/list_large/` endpoint performs both a write (UPDATE) and read (SELECT) operation:

```bash
curl http://127.0.0.1:8000/list_large/
```

Expected response (fast, < 1 second):
```json
{
  "emails": [...],
  "count": 10,
  "updated_id": 752
}
```

## Step 5: Demonstrate Blocking Behavior

### Option A: Three Terminal Demonstration (Manual)

**Terminal 1** - Server is already running via docker-compose

**Terminal 2** - Continuous API requests:
```bash
while true; do
  echo "[$(date +%H:%M:%S)] Request";
  curl -s --max-time 3 http://127.0.0.1:8000/list_large/ > /dev/null && echo " ✅ SUCCESS" || echo " ❌ BLOCKED/TIMEOUT";
  sleep 0.5;
done
```

**Terminal 3** - Run the migration:
```bash
docker compose exec web python manage.py migrate demoapp 0002
```

**What you'll observe:**
- Terminal 2 shows continuous SUCCESS messages before migration
- Once Terminal 3 starts the migration, Terminal 2 shows BLOCKED/TIMEOUT
- Blocking lasts for the entire duration of index creation (~35 seconds with 10M rows)
- After migration completes, Terminal 2 returns to SUCCESS messages

### Option B: Automated Single-Command Demonstration

Run this single command to see the full demonstration:

```bash
(for i in {1..60}; do
  echo "[$(date +%H:%M:%S)] Request $i";
  curl -s --max-time 3 http://127.0.0.1:8000/list_large/ > /dev/null && echo " ✅ SUCCESS" || echo " ❌ BLOCKED/TIMEOUT";
  sleep 0.5;
done) &
sleep 2 &&
echo "🚀 STARTING MIGRATION..." &&
docker compose exec -T web python manage.py migrate demoapp 0002 &&
echo "✅ MIGRATION COMPLETE" &&
wait
```

**Expected output:**
```
[23:18:32] Request 1
 ✅ SUCCESS
[23:18:32] Request 2
 ✅ SUCCESS
🚀 STARTING MIGRATION...
[23:18:35] Request 7
 ❌ BLOCKED/TIMEOUT
[23:18:35] Request 8
 ❌ BLOCKED/TIMEOUT
[23:18:36] Request 9
 ❌ BLOCKED/TIMEOUT
...
[23:19:02] Request 60
 ❌ BLOCKED/TIMEOUT
✅ MIGRATION COMPLETE
```

## Step 6: Understand What Happened

During the migration:
- PostgreSQL acquired a SHARE UPDATE EXCLUSIVE lock on `large_email` table
- The lock allows reads (SELECT) but **blocks writes** (UPDATE/INSERT/DELETE)
- Every API request tried to UPDATE a row, so it was blocked
- The blocking lasted ~35 seconds (time to create index on 10M rows)
- In production, this means 35 seconds of API timeouts and failures

Check the migration timing:

```bash
docker compose logs web | grep -A 20 "Adding index to LargeEmail"
```

You'll see:
```
[2025-11-06 17:48:35.292] Adding index to LargeEmail.email...
...
[2025-11-06 17:49:10.288] ✓ LargeEmail index created
```

That's 35 seconds of downtime!

## Step 7: The Safe Way (CREATE INDEX CONCURRENTLY)

To avoid blocking, PostgreSQL supports `CREATE INDEX CONCURRENTLY`:

```python
# In a custom migration file
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import models, migrations

class Migration(migrations.Migration):
    atomic = False  # Required for CONCURRENTLY

    operations = [
        AddIndexConcurrently(
            model_name='largeemail',
            index=models.Index(fields=['email'], name='large_email_email_idx'),
        ),
    ]
```

**Benefits:**
- ✅ No blocking of reads or writes
- ✅ Application remains fully responsive
- ✅ Index creation takes longer, but no downtime

**Trade-offs:**
- Takes 2-3x longer to create the index
- Cannot run in a transaction (requires `atomic = False`)
- Only works on PostgreSQL (not SQLite, MySQL < 5.6)

## Step 8: Clean Up

To reset and try again:

```bash
# Stop and remove everything
docker compose down -v

# Start fresh
docker compose up --build -d
```

## Key Takeaways

1. **Standard CREATE INDEX blocks writes** on PostgreSQL (INSERT/UPDATE/DELETE)
2. **Reads are NOT blocked** (SELECT still works) - this is why you need writes in your endpoint
3. **On 10M rows, index creation takes ~35 seconds** causing 35 seconds of API failures
4. **In production, this means downtime** - users see timeouts and errors
5. **Solution: Use CREATE INDEX CONCURRENTLY** on PostgreSQL to avoid blocking

## Additional Commands

### Check table structure:
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_email"
```

### Check active locks during migration:
```bash
# Run this in another terminal while migration is running
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT pid, usename, state, query, wait_event_type, wait_event
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state != 'idle';
"
```

### Monitor blocking queries:
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query,
       blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.granted
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"
```

### View index size:
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND tablename = 'large_email';
"
```

## Troubleshooting

### Container logs showing errors:
```bash
docker compose logs -f web
docker compose logs -f db
```

### Database connection issues:
```bash
# Check if database is ready
docker compose exec db pg_isready -U postgres
```

### Django server not responding:
```bash
# Restart web container
docker compose restart web
```

### Out of memory during seeding:
```bash
# Use smaller batch size
docker compose exec web python manage.py seed_large_table --large-count 1000000 --batch-size 5000
```
