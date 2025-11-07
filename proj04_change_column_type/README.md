# Project 04: Changing Column Type

This project demonstrates the risks of changing a column's data type on large tables in Django.

## The Problem

When you change a column's type (e.g., `CharField` to `DateTimeField`), the migration will:
1. Create a new column with the new type
2. **Copy and convert all existing data**
3. Drop the old column and rename the new one
4. Hold locks during this process
5. Block reads and writes until complete

On a table with millions of rows, this can take significant time and cause downtime.

## Demo Setup

### 1. Navigate to Project Directory

```bash
cd proj04_change_column_type
```

### 2. Activate Virtual Environment

```bash
source ../venv/bin/activate
```

### 3. Run Initial Migration

```bash
python manage.py migrate
```

### 4. Seed the Tables

```bash
# Creates 10 rows in SmallRecord and 5,000,000 rows in LargeRecord (default)
python manage.py seed_large_table

# Optional: Create fewer rows for faster testing
python manage.py seed_large_table --large-count 1000000
```

**Note:** The seed data creates `created_at` values as strings like "2024-01-01 10:00:00".

### 5. Start the Development Server

```bash
python manage.py runserver
```

Test the endpoint:
```bash
curl http://127.0.0.1:8000/list_large/
```

## Demonstrating the Risky Migration

The models have `created_at` changed from `CharField` to `DateTimeField`. This demonstrates the WRONG way to change column types.

### Step 1: Check Current Migration State

```bash
python manage.py showmigrations demoapp
```

You should see:
```
demoapp
 [X] 0001_initial
 [ ] 0002_alter_largerecord_created_at_and_more
```

### Step 2: Run the Column Type Change Migration

**Migration Up (Apply the type change):**
```bash
python manage.py migrate demoapp 0002
```

Watch the timing output. You'll see:
- SmallRecord column changed instantly (10 rows)
- LargeRecord column change takes much longer (5M rows - rewrites entire table!)

**Migration Down (Rollback):**
```bash
python manage.py migrate demoapp 0001
```

This reverts the column back to CharField.

**Migration Up Again:**
```bash
python manage.py migrate demoapp 0002
```

### Step 3: Observe Table Locking During Migration

To demonstrate how this migration blocks queries:

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

## The Safe Way: New Column + Copy + Swap

The project demonstrates the safe approach with migrations 0003, 0004, and 0005.

### Migration 0003: Add New Column with Correct Type (SAFE - Instant)

Adds `created_at_new` as a nullable DateTimeField:

```python
class LargeRecord(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField()  # Wrong way column
    created_at_new = models.DateTimeField(null=True, blank=True)  # RIGHT WAY: New column
```

**Run migration:**
```bash
python manage.py migrate demoapp 0003
```

This is **fast** - just adds a nullable column, no data copying!

### Migration 0004: Backfill Data in Batches (SAFE - Short locks)

Copies data from `created_at` to `created_at_new` in batches:

```python
def backfill_created_at_new(apps, schema_editor):
    LargeRecord = apps.get_model('demoapp', 'LargeRecord')
    batch_size = 100000

    while True:
        ids_to_update = list(
            LargeRecord.objects.filter(created_at_new__isnull=True)
                .values_list('id', flat=True)[:batch_size]
        )
        if not ids_to_update:
            break

        records = LargeRecord.objects.filter(id__in=ids_to_update)
        for record in records:
            record.created_at_new = record.created_at

        LargeRecord.objects.bulk_update(records, ['created_at_new'], batch_size=batch_size)
```

**Run migration:**
```bash
python manage.py migrate demoapp 0004
```

This runs in **batches** with short locks - safe!

### Migration 0005: Enforce NOT NULL Constraint (SAFE - Instant)

Makes `created_at_new` required after backfill:

```python
class LargeRecord(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField()  # Wrong way column
    created_at_new = models.DateTimeField()  # After backfill: enforce NOT NULL
```

**Run migration:**
```bash
python manage.py migrate demoapp 0005
```

This is **fast** - all rows already have values, just enforcing the constraint!

### Testing the Safe Approach

Rollback to before the safe migrations:
```bash
python manage.py migrate demoapp 0002
```

Then migrate forward step by step:
```bash
# Step 1: Add nullable column (instant)
python manage.py migrate demoapp 0003

# Step 2: Backfill in batches (safe)
python manage.py migrate demoapp 0004

# Step 3: Enforce NOT NULL (instant)
python manage.py migrate demoapp 0005
```

### Benefits of This Approach

- ✅ **Step 1 (0003)**: Add nullable column (instant, no locks)
- ✅ **Step 2 (0004)**: Backfill in batches (safe, short transactions)
- ✅ **Step 3 (0005)**: Enforce NOT NULL (instant, data already there)
- 🚀 The `/list_large/` endpoint remains responsive throughout!

### Optional Step 4: Swap Column Names

If you want to replace the old column entirely, you would:
1. Update application code to use `created_at_new`
2. Deploy code changes
3. Drop `created_at` column in a future migration
4. (Optional) Rename `created_at_new` to `created_at`

## Key Takeaways

### Wrong Way (Direct Column Type Change - Migration 0002)
- ❌ Single migration changes type and converts all data
- ❌ Rewrites entire table with locks
- ❌ Blocks all queries for extended time on large tables
- ❌ Risk of data loss if conversion fails

### Right Way (New Column + Copy + Swap - Migrations 0003, 0004, 0005)
- ✅ **Migration 0003**: Add `created_at_new` nullable column (instant)
- ✅ **Migration 0004**: Copy data in batches (safe, short locks)
- ✅ **Migration 0005**: Make `created_at_new` NOT NULL (instant)
- ✅ No downtime, table remains accessible
- 🚀 Can rollback and replay individual steps

## Migration Commands Reference

### Check Migration Status
```bash
python manage.py showmigrations demoapp
```

### Migrate Forward (Change Column Type)
```bash
# Migrate to a specific migration
python manage.py migrate demoapp 0002

# Or migrate all pending migrations
python manage.py migrate
```

### Migrate Backward (Revert Column Type)
```bash
# Rollback to migration 0001 (reverts to CharField)
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

## Common Pitfalls

1. **Data Loss**: Direct type changes can fail if data doesn't convert cleanly
2. **Downtime**: Large tables can be locked for minutes
3. **Memory**: Converting millions of rows at once can exhaust memory
4. **Rollback Issues**: Reverting a failed migration can be complex

Always test column type changes on a copy of production data first!
