# Demo Commands for proj07_add_foreign_key

This file contains step-by-step commands to demonstrate the **RISKY** practice of adding foreign key constraints to existing tables with millions of rows without validation optimization.

## Prerequisites

Ensure Docker and Docker Compose are installed on your system.

---

## Overview

This project demonstrates **why adding foreign key constraints to large tables causes table locks and downtime**:

1. **Migration 0001**: Initial state with `customer_id` as plain IntegerField (no FK constraint)
2. **Migration 0002**: **RISKY** - Adds ForeignKey constraint which triggers full table scan for validation

**The Problem:**
- PostgreSQL must validate that ALL 10 million `customer_id` values reference valid customers
- The entire `large_order` table is locked during validation (30-60 seconds for 10M rows)
- All queries to the table block/timeout during this period

**Models:**
- **Customer** - Parent table (100 customers)
- **SmallOrder** - 10 rows (FK addition is instant)
- **LargeOrder** - 10 million rows (FK addition locks table)

---

## Step 1: Start the Containers

```bash
cd proj07_add_foreign_key
docker compose up --build -d
```

This will:
- Start PostgreSQL 16 database on port 5436
- Build and start Django application
- Start Django dev server on http://localhost:8004

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
 [ ] 0002_remove_largeorder_customer_id_and_more
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
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT 'customer' as table_name, COUNT(*) as count FROM customer
UNION ALL
SELECT 'small_order', COUNT(*) FROM small_order
UNION ALL
SELECT 'large_order', COUNT(*) FROM large_order;
"
```

Expected output:
```
 table_name  |  count
-------------+----------
 customer    |      100
 small_order |       10
 large_order | 10000000
```

---

## Step 4: Test the Endpoint (Before Adding FK)

```bash
curl http://127.0.0.1:8004/list_large/
```

Expected response (fast, < 1 second):
```json
{
  "orders": [
    {"id": 1, "order_number": "LARGE-0000000001", "customer_id": 2, "total_amount": "101.00"},
    {"id": 2, "order_number": "LARGE-0000000002", "customer_id": 3, "total_amount": "102.00"},
    ...
  ],
  "count": 10
}
```

**Observation:** API responds instantly because there's no FK constraint yet!

---

## Step 5: Check Table Structure (Before Migration)

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_order"
```

Expected output:
```
                         Table "public.large_order"
    Column     |          Type          | Collation | Nullable | Default
---------------+------------------------+-----------+----------+---------
 id            | bigint                 |           | not null |
 order_number  | character varying(50)  |           | not null |
 customer_id   | integer                |           | not null |  <-- Plain integer, no FK!
 total_amount  | numeric(10,2)          |           | not null |
```

Notice `customer_id` is just an `integer` with no foreign key constraint.

---

## Step 6: Monitor API Continuously

Open a **second terminal** and run this monitoring script to continuously ping the API:

```bash
while true; do
  echo "[$(date +%H:%M:%S)] Testing API";

  if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8004/list_large/)" = "200" ]; then
    echo " ✅ /list_large/ SUCCESS";
  else
    echo " ❌ /list_large/ FAILED";
  fi

  echo "";
  sleep 1;
done
```

**Before migration 0002:**
```
[22:30:01] Testing API
 ✅ /list_large/ SUCCESS

[22:30:02] Testing API
 ✅ /list_large/ SUCCESS
```

---

## Step 7: Run Migration 0002 - Add Foreign Key (RISKY!)

In your **first terminal**, run the migration to add the foreign key constraint:

```bash
docker compose exec web python manage.py migrate demoapp 0002
```

Expected output:
```
Operations to perform:
  Target specific migration: 0002_remove_largeorder_customer_id_and_more, from demoapp
Running migrations:
  Applying demoapp.0002_remove_largeorder_customer_id_and_more...

[2025-11-07 22:30:15.123] Adding nullable FK customer to SmallOrder...
[2025-11-07 22:30:15.145] ✓ SmallOrder FK added

[2025-11-07 22:30:15.146] Adding nullable FK customer to LargeOrder...
```

**At this point, the migration will hang for 30-60 seconds while PostgreSQL validates 10 million rows!**

---

## Step 8: Observe API Blocking During Migration

Watch your **second terminal** (monitoring script):

**During migration 0002 (FK validation happening):**
```
[22:30:16] Testing API
 ❌ /list_large/ FAILED

[22:30:20] Testing API
 ❌ /list_large/ FAILED

[22:30:24] Testing API
 ❌ /list_large/ FAILED
```

**After migration completes:**
```
[2025-11-07 22:30:45.234] ✓ LargeOrder FK added
 OK

[22:30:46] Testing API
 ✅ /list_large/ SUCCESS

[22:30:47] Testing API
 ✅ /list_large/ SUCCESS
```

**Key Observation:**
- ❌ API is completely blocked during FK validation (30-60 seconds)
- All queries timeout with `--max-time 3`
- This represents **full downtime** in production!

---

## Step 9: Verify Foreign Key Was Added

Check the table structure again:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_order"
```

Expected output:
```
                         Table "public.large_order"
    Column    |          Type          | Collation | Nullable | Default
--------------+------------------------+-----------+----------+---------
 id           | bigint                 |           | not null |
 order_number | character varying(50)  |           | not null |
 customer_id  | bigint                 |           |          |  <-- Now a FK to customer!
 total_amount | numeric(10,2)          |           | not null |

Foreign-key constraints:
    "demoapp_largeorder_customer_id_fkey" FOREIGN KEY (customer_id) REFERENCES customer(id)
```

The FK constraint is now present!

---

## Step 10: Check Foreign Key Constraints

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE contype = 'f' AND connamespace = 'public'::regnamespace;
"
```

Expected output:
```
                constraint_name                | table_name  | referenced_table
----------------------------------------------+-------------+------------------
 demoapp_smallorder_customer_id_fkey          | small_order | customer
 demoapp_largeorder_customer_id_fkey          | large_order | customer
```

---

## Step 11: The SAFE Way to Add Foreign Keys

This project demonstrates the **WRONG WAY** (direct FK addition with validation). Here's the **RIGHT WAY** using PostgreSQL's `NOT VALID` feature:

### Safe FK Addition Process (2 Steps):

**Step 1: Add FK constraint as NOT VALID (instant, no validation)**
```sql
ALTER TABLE large_order
ADD CONSTRAINT fk_customer
FOREIGN KEY (customer_id) REFERENCES customer(id)
NOT VALID;
```
- This creates the FK constraint WITHOUT validating existing rows
- Takes < 1 second regardless of table size
- New inserts/updates WILL be validated
- Existing rows are NOT validated yet

**Step 2: Validate constraint separately (can be done during low-traffic period)**
```sql
ALTER TABLE large_order
VALIDATE CONSTRAINT fk_customer;
```
- Validates all existing rows
- Still takes time (30-60 seconds for 10M rows)
- But you control WHEN this happens
- Can be run during maintenance window

### Django Implementation (Safe Way):

```python
from django.db import migrations
from django.db.models import Q

class Migration(migrations.Migration):
    operations = [
        # Step 1: Add FK as NOT VALID
        migrations.RunSQL(
            sql="""
                ALTER TABLE large_order
                ADD CONSTRAINT fk_customer
                FOREIGN KEY (customer_id) REFERENCES customer(id)
                NOT VALID;
            """,
            reverse_sql="ALTER TABLE large_order DROP CONSTRAINT fk_customer;"
        ),

        # Step 2: Validate in separate migration (deploy later)
        # migrations.RunSQL(
        #     sql="ALTER TABLE large_order VALIDATE CONSTRAINT fk_customer;",
        #     reverse_sql=migrations.RunSQL.noop
        # ),
    ]
```

### Timeline Comparison:

**RISKY Approach (This Project - Migration 0002):**
```
0:00 ────────────[DOWNTIME: 30-60 seconds]──────────── 1:00
     [ADD FK with validation]
     ❌ API completely blocked
     ❌ All queries timeout
     ❌ Full table scan happens immediately
```

**SAFE Approach (NOT VALID + VALIDATE):**
```
Day 1: [ADD FK NOT VALID] ──→ Deploy (< 1 second, zero downtime)
         ✅ New data validated
         ✅ API fully responsive
         ✅ Existing data not validated yet

Day 2: [VALIDATE CONSTRAINT] ──→ During maintenance window
         ✅ Controlled timing
         ✅ Can be done during low-traffic period
         ✅ Progress can be monitored
```

---

## Additional Commands

### Monitor active queries and locks during migration:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT
    pid,
    usename,
    state,
    query_start,
    wait_event_type,
    wait_event,
    LEFT(query, 100) as query_snippet
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state != 'idle'
ORDER BY query_start;
"
```

### Check table sizes:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('customer', 'small_order', 'large_order')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

Expected output (10M rows):
```
 schemaname | tablename   |  size
------------+-------------+---------
 public     | large_order | 850 MB
 public     | customer    | 24 kB
 public     | small_order | 16 kB
```

### Check if FK constraint exists:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT conname, contype, convalidated
FROM pg_constraint
WHERE conrelid = 'large_order'::regclass AND contype = 'f';
"
```

Output after migration 0002:
```
              conname               | contype | convalidated
------------------------------------+---------+--------------
 demoapp_largeorder_customer_id_fkey|    f    |      t
```
- `contype = 'f'` means foreign key
- `convalidated = t` means constraint is validated (risky approach)
- `convalidated = f` would mean NOT VALID (safe approach)

### Sample data inspection:

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT o.id, o.order_number, o.customer_id, c.name as customer_name, o.total_amount
FROM large_order o
JOIN customer c ON o.customer_id = c.id
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

### ❌ What This Project Shows (WRONG WAY - Migration 0002)

**Adding FK constraint directly causes:**
- Full table scan to validate ALL existing rows (10M rows = 30-60 seconds)
- Exclusive table lock during validation (blocks ALL queries)
- Complete application downtime (API returns timeouts)
- No control over when validation happens

**Why migration 0002 takes so long:**
- PostgreSQL must verify every `customer_id` references a valid customer
- For 10 million rows, this means 10 million lookups
- The table is locked during this entire process
- No way to cancel or pause once started

### ✅ Safe Foreign Key Addition Pattern (RIGHT WAY)

**Always use the NOT VALID pattern:**

**Step 1: Add FK as NOT VALID**
```sql
ALTER TABLE large_order
ADD CONSTRAINT fk_customer
FOREIGN KEY (customer_id) REFERENCES customer(id)
NOT VALID;
```
- **Instant** (< 1 second, metadata-only)
- **Zero downtime** (no table lock)
- New inserts/updates are validated
- Existing data can have invalid references (temporarily)

**Step 2: Validate separately**
```sql
ALTER TABLE large_order
VALIDATE CONSTRAINT fk_customer;
```
- Run during maintenance window or low-traffic period
- Still takes time but you control WHEN
- Can be monitored and canceled if needed
- Can be run in batches using custom logic

### 📊 Performance Comparison

| Metric | Direct FK Addition (Risky) | NOT VALID + VALIDATE (Safe) |
|--------|----------------------------|------------------------------|
| Initial FK Creation | 30-60 seconds | < 1 second |
| API Downtime | 30-60 seconds | **0 seconds** (initial) |
| Table Lock Duration | 30-60 seconds | < 1 second (initial) |
| Validation Control | ❌ No control | ✅ Full control |
| Can Cancel/Pause | ❌ No | ✅ Yes |
| Production Ready | ❌ No | ✅ Yes |

### 🎯 When to Use Each Pattern

**Always use NOT VALID pattern when:**
- Table has 100,000+ rows
- Zero downtime is required
- Production environment
- High-traffic applications
- Need control over validation timing

**Only use direct FK addition when:**
- Table has < 10,000 rows
- Downtime is acceptable
- Non-production environment
- Data integrity is critical immediately

### 🔍 Why NOT VALID Works

**How PostgreSQL handles NOT VALID:**

1. **Initial creation** (NOT VALID):
   - Creates FK constraint metadata
   - Does NOT scan existing rows
   - Validates NEW inserts/updates only
   - Takes < 1 second

2. **Later validation** (VALIDATE):
   - Scans all existing rows
   - Checks referential integrity
   - Can be run during maintenance window
   - Can be cancelled if needed

**Benefits:**
- Separates constraint creation from validation
- Gives you control over timing
- Allows progressive migration strategy
- Maintains data integrity for new operations

---

## Troubleshooting

### Migration hangs indefinitely:

Check for blocking queries:
```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT pid, query, state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state != 'idle';
"
```

### Kill blocking queries (if needed):

```bash
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state = 'active' AND query LIKE '%ALTER TABLE%';
"
```

### Container logs:

```bash
docker compose logs -f web
docker compose logs -f db
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
- **proj04_safe_backfill** - Shows safe column type change pattern
- **proj05_drop_column** - Shows dangers of dropping columns without removing code references

See the main `CLAUDE.md` for all 10 risky migration scenarios.

---

## Advanced: Implementing NOT VALID in Django

### Custom Migration with NOT VALID:

Create `0002_add_fk_not_valid.py`:

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('demoapp', '0001_initial'),
    ]

    operations = [
        # Remove old customer_id field
        migrations.RemoveField(
            model_name='largeorder',
            name='customer_id',
        ),

        # Add FK constraint as NOT VALID (instant)
        migrations.RunSQL(
            sql="""
                ALTER TABLE large_order
                ADD COLUMN customer_id BIGINT;

                ALTER TABLE large_order
                ADD CONSTRAINT demoapp_largeorder_customer_id_fkey
                FOREIGN KEY (customer_id) REFERENCES customer(id)
                NOT VALID;
            """,
            reverse_sql="""
                ALTER TABLE large_order DROP CONSTRAINT demoapp_largeorder_customer_id_fkey;
                ALTER TABLE large_order DROP COLUMN customer_id;
            """
        ),
    ]
```

Then create `0003_validate_fk.py` (deploy later):

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('demoapp', '0002_add_fk_not_valid'),
    ]

    operations = [
        # Validate the FK constraint (run during maintenance window)
        migrations.RunSQL(
            sql="ALTER TABLE large_order VALIDATE CONSTRAINT demoapp_largeorder_customer_id_fkey;",
            reverse_sql=migrations.RunSQL.noop
        ),
    ]
```

---

## Next Steps

After this demo, explore:
- Implementing NOT VALID constraints in your Django projects
- Creating monitoring for long-running migrations
- Setting up migration rollback procedures
- Using pg_stat_activity to monitor migration progress
- Implementing progressive migration strategies
