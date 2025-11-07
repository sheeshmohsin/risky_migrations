# Project 05: Dropping a Column

This project demonstrates the risks of dropping a column from large tables in Django.

## The Problem

When you drop a column directly, Django will:
1. Execute an `ALTER TABLE DROP COLUMN` statement
2. **Lock the table** during the operation
3. Block reads and writes until complete
4. Risk breaking production if code still references the column

On a table with millions of rows, dropping a column can cause downtime and application errors.

## Demo Setup

### 1. Navigate to Project Directory

```bash
cd proj05_drop_column
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
# Creates 10 rows in SmallProduct and 5,000,000 rows in LargeProduct (default)
python manage.py seed_large_table

# Optional: Create fewer rows for faster testing
python manage.py seed_large_table --large-count 100000
```

### 5. Start the Development Server

```bash
python manage.py runserver
```

Test the endpoint:
```bash
curl http://127.0.0.1:8000/list_large/
```

## Demonstrating the Risky Migration

### The WRONG Way: Direct Column Drop (Migration 0002)

This demonstrates dropping the `legacy_code` column directly without preparation.

#### Step 1: Check Current Migration State

```bash
python manage.py showmigrations demoapp
```

You should see:
```
demoapp
 [X] 0001_initial
 [ ] 0002_remove_largeproduct_legacy_code_and_more
```

#### Step 2: Run the Column Drop Migration

**Migration Up (Drop the column):**
```bash
python manage.py migrate demoapp 0002
```

Watch the timing output. You'll see:
- SmallProduct column dropped instantly (10 rows)
- LargeProduct column drop takes longer (millions of rows)

**Migration Down (Restore the column):**
```bash
python manage.py migrate demoapp 0001
```

This will restore the `legacy_code` column.

#### Step 3: Observe Table Locking During Migration

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

## The RIGHT Way: Deprecate Logically First

The safe approach to dropping a column involves multiple steps with zero downtime:

### Step 1: Mark Column as Deprecated (Code Change)

Before dropping the column, you should:

1. **Update your application code** to stop writing to `legacy_code`
2. **Update your application code** to stop reading from `legacy_code`
3. **Deploy this code change** to production
4. **Wait** to ensure all application instances are updated

This ensures no code references the column before you drop it.

### Step 2: Make Column Nullable (Optional Safety Step)

If the column has a NOT NULL constraint, make it nullable first:

```python
class LargeProduct(models.Model):
    name = models.CharField(max_length=100)
    legacy_code = models.CharField(max_length=50, null=True, blank=True)  # Made nullable
    price = models.DecimalField(max_digits=10, decimal_places=2)
```

Run migration:
```bash
python manage.py makemigrations
python manage.py migrate
```

This is fast (just removes the constraint).

### Step 3: Monitor Production

- Check logs to ensure no errors about missing columns
- Verify no queries are using the column
- Wait for a safe period (days/weeks depending on confidence)

### Step 4: Drop the Column

Only after confirming the column is unused, drop it:

```python
class LargeProduct(models.Model):
    name = models.CharField(max_length=100)
    # legacy_code removed
    price = models.DecimalField(max_digits=10, decimal_places=2)
```

Run migration:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Benefits of This Approach

- ✅ Zero downtime - code stops using column first
- ✅ Reversible - can rollback code changes easily
- ✅ Safe - no risk of breaking production
- ✅ Monitored - time to observe and catch issues
- 🚀 Column drop is just cleanup, not a critical operation

## Key Takeaways

### Wrong Way (Direct Column Drop - Migration 0002)
- ❌ Drop column while code might still use it
- ❌ Table locked during operation
- ❌ Risk of application errors if code references column
- ❌ Difficult to rollback if issues arise

### Right Way (Deprecate Logically First)
- ✅ **Step 1**: Update code to stop using the column
- ✅ **Step 2**: Deploy code changes and monitor
- ✅ **Step 3**: Make column nullable (optional safety)
- ✅ **Step 4**: Wait and verify no usage
- ✅ **Step 5**: Drop the column as cleanup
- ✅ Zero downtime, fully reversible, safe

## Migration Commands Reference

### Check Migration Status
```bash
python manage.py showmigrations demoapp
```

### Migrate Forward (Drop Column)
```bash
# Migrate to a specific migration
python manage.py migrate demoapp 0002

# Or migrate all pending migrations
python manage.py migrate
```

### Migrate Backward (Restore Column)
```bash
# Rollback to migration 0001 (restores legacy_code column)
python manage.py migrate demoapp 0001
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

1. **Breaking Production**: Dropping a column while code still references it causes immediate errors
2. **Table Locking**: Large tables can be locked for extended periods during column drop
3. **No Easy Rollback**: Once column is dropped, data is gone
4. **Foreign Key Constraints**: Dropping columns with foreign keys can cascade to other tables

Always deprecate columns in code first, then drop them after confirming they're unused!

## Additional Notes

### Why Column Drops Can Be Fast

In some databases (like SQLite), dropping a column is a metadata-only operation and can be fast. However:
- In PostgreSQL < 11, dropping columns could require a table rewrite
- In MySQL, it depends on the storage engine
- Even if fast, you still risk breaking code that references the column

The **real risk** of dropping columns is:
1. **Application errors** if code still uses the column
2. **Data loss** that's hard to recover
3. **Deployment coordination** between code and migrations

### Production Best Practices

1. **Code First, Schema Second**: Always update code to stop using a column before dropping it
2. **Gradual Rollout**: Deploy code changes gradually with monitoring
3. **Wait Period**: Give yourself days or weeks to catch issues
4. **Nullable Transition**: Make columns nullable as an intermediate step
5. **Backup First**: Always have recent backups before dropping columns
