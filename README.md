# Risky Database Migrations - Django Day India 2025

**A comprehensive demonstration of common database migration anti-patterns and their safe alternatives for production Django applications.**

---

## 📋 Overview

This repository contains **10 independent Django demo projects** that demonstrate risky database migration scenarios on production-like databases. Each project shows a common migration anti-pattern and its safe alternative, using PostgreSQL 16 and Django 4.2+.

**Presentation:** Django Day India 2025
**Topic:** Safe Database Migrations at Scale
**Focus:** Zero-downtime migration patterns for production environments

---

## 🎯 Purpose

Database migrations can cause serious production issues:
- **Table locks** blocking all queries (30-60 seconds or more)
- **Complete application downtime** during schema changes
- **Cascading failures** when code references dropped columns
- **Performance degradation** from improper indexing strategies

This repository provides **hands-on demonstrations** of:
- ✅ What goes wrong with naive migration approaches
- ✅ How to implement safe, zero-downtime alternatives
- ✅ Real-world patterns used by high-traffic applications

---

## 🗂️ Project Structure

Each project is a self-contained Django application with Docker setup:

```
risky-migrations/
├── proj01_add_not_null_constraint/   # ❌ Adding NOT NULL locks table
├── proj01_safe_backfill/             # ✅ Safe: nullable → backfill → NOT NULL
├── proj03_indexes/                   # ❌ Index creation blocks reads/writes
├── proj03_safe_backfill/             # ✅ Safe: CREATE INDEX CONCURRENTLY
├── proj04_change_column_type/        # ❌ Column type change rewrites table
├── proj04_safe_backfill/             # ✅ Safe: add new column → copy → swap
├── proj05_drop_column/               # ❌ Dropping columns breaks code
├── proj07_add_foreign_key/           # ❌ FK validation blocks everything
├── proj07_safe_backfill/             # ✅ Safe: NOT VALID → VALIDATE separately
├── venv/                             # Shared Python virtual environment
├── CLAUDE.md                         # Development guidance
└── README.md                         # This file
```

### Status

**Completed:** 7 of 10 projects
**In Progress:** Projects 2, 6, 8, 9, 10 (planned)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB+ RAM recommended
- ~5GB disk space per project

### Running a Demo Project

Each project follows the same pattern:

```bash
# 1. Navigate to project
cd proj07_safe_backfill

# 2. Start containers
docker compose up --build -d

# 3. Check migrations
docker compose exec web python manage.py showmigrations demoapp

# 4. Seed database (10 million rows)
docker compose exec web python manage.py seed_large_table --large-count 10000000

# 5. Run migrations and observe
docker compose exec web python manage.py migrate demoapp 0002

# 6. Clean up
docker compose down -v
```

### Testing API Responsiveness

Each project includes a `/list_large/` endpoint to demonstrate locking:

```bash
# Monitor API during migrations
while true; do
  echo "[$(date +%H:%M:%S)] Testing API";
  if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:8005/list_large/)" = "200" ]; then
    echo " ✅ SUCCESS";
  else
    echo " ❌ FAILED (blocked by migration)";
  fi
  echo "";
  sleep 1;
done
```

---

## 📚 The 10 Migration Scenarios

### 1. Adding NOT NULL Constraints

**Problem:** Adding NOT NULL to existing nullable column causes full table validation lock.

- **proj01_add_not_null_constraint** - ❌ Direct NOT NULL addition (30-60s downtime)
- **proj01_safe_backfill** - ✅ Safe pattern: nullable → batch backfill → NOT NULL

**Key Takeaway:** Always backfill data first, then add constraint.

---

### 2. [TODO] TBD

---

### 3. Index Creation

**Problem:** Standard index creation blocks both reads and writes.

- **proj03_indexes** - ❌ Standard `CREATE INDEX` (blocks table)
- **proj03_safe_backfill** - ✅ Safe pattern: `CREATE INDEX CONCURRENTLY`

**Key Takeaway:** Use PostgreSQL's `CONCURRENTLY` option for zero-downtime indexing.

---

### 4. Changing Column Types

**Problem:** Direct column type change rewrites entire table (locks for minutes).

- **proj04_change_column_type** - ❌ Direct ALTER TYPE (30-60s blocking)
- **proj04_safe_backfill** - ✅ Safe pattern: add new column → batch copy → swap → drop old

**Key Takeaway:** Never change column types directly on large tables.

**Performance:**
- Risky: 30-60s full table lock
- Safe: 8-10 minutes batched (0.4s lock per 10K rows, zero downtime)

---

### 5. Dropping Columns

**Problem:** Dropping columns before removing code references breaks application.

- **proj05_drop_column** - ❌ Drop column while code still uses it

**Key Takeaway:** Always remove code references → deploy → then drop column.

**Safe Pattern:**
1. Remove all code references to the column
2. Deploy application code
3. Monitor production (ensure no errors)
4. Drop column in separate migration

---

### 6. [TODO] Large Backfills

---

### 7. Adding Foreign Key Constraints

**Problem:** FK validation scans entire table, blocking reads and writes.

- **proj07_add_foreign_key** - ❌ Direct FK addition with validation (30-60s downtime)
- **proj07_safe_backfill** - ✅ Safe pattern: `NOT VALID` → `VALIDATE` separately

**Key Takeaway:** Use PostgreSQL's `NOT VALID` to split FK creation from validation.

**Pattern:**
```sql
-- Step 1: Add FK as NOT VALID (instant, no validation)
ALTER TABLE large_order
ADD CONSTRAINT fk_customer
FOREIGN KEY (customer_id) REFERENCES customer(id)
NOT VALID;

-- Step 2: Validate separately (run during maintenance window)
ALTER TABLE large_order VALIDATE CONSTRAINT fk_customer;
```

**Lock Behavior:**
- Risky approach: `ACCESS EXCLUSIVE` lock (blocks reads AND writes)
- Safe approach: `SHARE UPDATE EXCLUSIVE` lock (blocks only writes during validation)

---

### 8-10. [TODO] Coming Soon

---

## 🎓 Key Patterns & Best Practices

### The Golden Rule

**Never perform blocking operations on large tables during business hours.**

### Safe Migration Checklist

✅ **Assess table size** - How many rows?
✅ **Identify lock type** - What lock does this migration take?
✅ **Estimate duration** - How long will it block?
✅ **Plan rollback** - Can we reverse this safely?
✅ **Test on production copy** - Never test on production first!
✅ **Monitor during migration** - Watch for blocking queries

### Common Safe Patterns

1. **Add-Transform-Switch-Drop**
   - Add new column (instant)
   - Backfill data in batches (no blocking)
   - Update application to use new column
   - Drop old column (instant)

2. **NOT VALID → VALIDATE**
   - Add constraint as NOT VALID (instant)
   - New data is validated
   - Validate existing data separately (controlled timing)

3. **CONCURRENTLY**
   - PostgreSQL's `CONCURRENTLY` option
   - Works for indexes and some constraints
   - Takes longer but doesn't block

4. **Batch Processing**
   - Process 10,000-100,000 rows per batch
   - Commit between batches
   - Short locks instead of one long lock

---

## 🔧 Project Anatomy

Each project follows a consistent structure:

### Models

```python
class SmallTable(models.Model):
    # 10 rows - migrations complete instantly
    # Used to show that pattern works without side effects

class LargeTable(models.Model):
    # Millions of rows - migrations demonstrate locks/downtime
    # Used to show real-world production impact
```

### Migrations

- **0001_initial** - Starting state
- **0002_risky** - Demonstrates the anti-pattern
- **0003_safe** - Shows the safe alternative (when applicable)

### Management Commands

```bash
# Seed database with realistic data
python manage.py seed_large_table --large-count 10000000

# Optimized batch size (10K rows per batch)
# Progress reporting every 100K rows
```

### API Endpoints

- `/list_large/` - Read operation (SELECT query)
- `/update_order/` - Write operation (UPDATE query)

Used to demonstrate table locking during migrations.

---

## 📊 Performance Metrics

Example from **proj04_safe_backfill** (column type change):

| Metric | Risky Approach | Safe Approach |
|--------|---------------|---------------|
| Total Time (10M rows) | 30-60 seconds | 8-10 minutes |
| API Downtime | 30-60 seconds | **0 seconds** |
| Lock Duration | Full table lock | 0.4s per 10K rows |
| Rollback Safety | Risky | Safe at each step |
| Progress Visibility | None | Real-time tracking |
| Memory Usage | High | Low (batched) |

**Conclusion:** Slower overall, but zero downtime = production-safe.

---

## 🐳 Docker Configuration

Each project uses unique ports to avoid conflicts:

| Project | Django Port | PostgreSQL Port |
|---------|-------------|-----------------|
| proj01_add_not_null_constraint | 8000 | 5432 |
| proj01_safe_backfill | 8001 | 5433 |
| proj03_indexes | 8000 | 5432 |
| proj03_safe_backfill | 8001 | 5433 |
| proj04_change_column_type | 8002 | 5432 |
| proj04_safe_backfill | 8002 | 5434 |
| proj05_drop_column | 8003 | 5435 |
| proj07_add_foreign_key | 8004 | 5436 |
| proj07_safe_backfill | 8005 | 5437 |

---

## 📝 Demo Commands

Each project includes a `DEMO_COMMANDS.md` file with:
- Step-by-step setup instructions
- Seeding commands
- Migration execution steps
- Monitoring scripts
- Performance comparison
- Troubleshooting tips

Example: [proj07_safe_backfill/DEMO_COMMANDS.md](proj07_safe_backfill/DEMO_COMMANDS.md)

---

## 🛠️ Development

### Creating New Projects

Follow the pattern in existing projects:

```bash
# 1. Create Django project
cd risky-migrations
django-admin startproject proj##_scenario_name
cd proj##_scenario_name
python manage.py startapp demoapp

# 2. Copy boilerplate from existing project
cp ../proj07_safe_backfill/docker-compose.yml .
cp ../proj07_safe_backfill/Dockerfile .
cp ../proj07_safe_backfill/requirements.txt .
cp ../proj07_safe_backfill/.env.example .env

# 3. Update ports in docker-compose.yml
# 4. Create models (SmallTable + LargeTable pattern)
# 5. Create views and URLs
# 6. Create seed command
# 7. Generate and test migrations
# 8. Write DEMO_COMMANDS.md
```

### Useful Commands

```bash
# Check migration status
python manage.py showmigrations demoapp

# Rollback to specific migration
python manage.py migrate demoapp 0001

# Access PostgreSQL
docker compose exec db psql -U postgres -d risky_migrations

# Check table structure
docker compose exec db psql -U postgres -d risky_migrations -c "\d large_table"

# Monitor active queries
docker compose exec db psql -U postgres -d risky_migrations -c "
SELECT pid, usename, state, query_start, query
FROM pg_stat_activity
WHERE datname = 'risky_migrations' AND state != 'idle';
"
```

---

## 🎯 Learning Objectives

After working through these demos, you'll understand:

1. **Lock Types**
   - `ACCESS EXCLUSIVE` - Blocks everything
   - `SHARE UPDATE EXCLUSIVE` - Blocks only writes
   - Impact on application availability

2. **Migration Patterns**
   - Add-backfill-enforce pattern
   - NOT VALID constraints
   - Concurrent operations
   - Batch processing

3. **Production Strategies**
   - Pre-deployment testing
   - Monitoring during migrations
   - Rollback procedures
   - Communication with stakeholders

4. **PostgreSQL Internals**
   - Table rewrites vs metadata changes
   - Constraint validation behavior
   - Index creation mechanisms
   - MVCC and locking

---

## 📖 Additional Resources

### Documentation

- [PostgreSQL ALTER TABLE documentation](https://www.postgresql.org/docs/current/sql-altertable.html)
- [Django Migrations documentation](https://docs.djangoproject.com/en/4.2/topics/migrations/)
- [PostgreSQL Lock Conflicts](https://www.postgresql.org/docs/current/explicit-locking.html)

### Related Articles

- [Zero-downtime Postgres migrations](https://gocardless.com/blog/zero-downtime-postgres-migrations-the-hard-parts/)
- [Strong Migrations for Rails](https://github.com/ankane/strong_migrations) (concepts apply to Django)
- [Braintree's Safe Postgres Schema Changes](https://medium.com/braintree-product-technology/postgresql-at-scale-database-schema-changes-without-downtime-20d3749ed680)

---

## 🤝 Contributing

This repository was created for Django Day India 2025. Contributions are welcome!

### Ideas for New Projects

- **proj02** - TBD
- **proj06_large_backfills** - Mass updates locking tables
- **proj08_drop_indexes** - Index drops impacting performance
- **proj09_alter_defaults** - Unnecessary locks from default changes
- **proj10_large_deletes** - Deleting millions of rows safely

### How to Contribute

1. Fork the repository
2. Create a new project following the established pattern
3. Include comprehensive `DEMO_COMMANDS.md`
4. Test thoroughly with Docker
5. Submit pull request

---

## 📄 License

MIT License - Feel free to use for educational purposes.

---

## 👥 Author

Created for **Django Day India 2025**
Presenter: Sheesh Mohsin

---

## 🙏 Acknowledgments

- Django community for excellent migration framework
- PostgreSQL team for powerful database features
- Django Day India organizers and attendees

---

## 💡 Key Takeaways

1. **Always test migrations on production-like data** (millions of rows)
2. **Understand PostgreSQL lock types** and their impact
3. **Use safe patterns** even if they take longer
4. **Monitor during migrations** - don't deploy and walk away
5. **Zero downtime is achievable** with proper planning

**Remember:** A migration that takes 10 minutes with zero downtime is better than one that takes 1 minute but blocks everything.

---

**Happy Migrating! 🚀**

For questions or demo requests, please open an issue or contact the maintainer.
