# Celery Saturation Fixes for EVE Wargames

This document outlines the fixes implemented to resolve Celery task queue saturation issues.

## 🚨 Problems Identified

### 1. **Massive Task Accumulation**
- `orchestrate_killmail_collection` runs hourly and schedules individual tasks for every warzone system
- With 50+ systems: ~300 tasks/hour at 5-minute intervals
- During 8-hour downtime: 2,400+ queued tasks accumulate
- Tasks had no expiration - they waited indefinitely

### 2. **Aggressive Retry Policies**
- Tasks had 2-3 retries with exponential backoff
- Failed tasks kept retrying and blocking the queue
- Exponential backoff created long delays (up to 4+ minutes)

### 3. **No Downtime Protection**
- Tasks scheduled during downtime would all execute when workers restarted
- No mechanism to skip stale/irrelevant tasks
- Beat scheduler continued creating tasks even when workers were down

### 4. **Database Connection Issues**
- Sessions not properly closed on errors before retries
- Potential connection pool exhaustion

## ✅ Fixes Implemented

### 1. **Task Expiration & Reliability**
```python
# Global Celery configuration
task_expires=7200,  # Tasks expire after 2 hours
task_acks_late=True,  # Acknowledge only after completion
task_reject_on_worker_lost=True,  # Reject tasks if worker crashes
task_default_rate_limit='10/m',  # Max 10 tasks per minute per worker
```

### 2. **Minimal Retry Policy**
- **All tasks now have max_retries=1** (down from 2-3)
- **Fixed 5-minute retry delay** (no more exponential backoff)
- Faster failure detection and recovery

### 3. **Stale Task Detection**
```python
def should_skip_stale_task(task_eta=None, max_age_minutes=90):
    """Skip tasks that are too old to be relevant"""
```
- Tasks older than 90 minutes are automatically skipped
- Prevents execution of tasks scheduled during downtime
- Uses `celery.exceptions.Ignore` to cleanly skip tasks

### 4. **Individual Task Expiration**
```python
# Orchestration now sets expiration on each scheduled task
task_result = collect_system_killmails.apply_async(
    args=[system_id],
    eta=execution_time,
    expires=expiration_time  # 2 hours after scheduled time
)
```

### 5. **Improved Database Session Management**
```python
db = None
try:
    db = SessionLocal()
    # ... task logic
finally:
    if db:
        db.close()
```

## 🛠️ Monitoring & Management

### New Monitoring Script
Use `backend/scripts/celery_monitor.py` to manage the queue:

```bash
# Check queue statistics
python backend/scripts/celery_monitor.py stats

# Purge all tasks (emergency use)
python backend/scripts/celery_monitor.py purge

# Remove stale tasks (older than 2 hours)
python backend/scripts/celery_monitor.py revoke-stale

# Check worker status
python backend/scripts/celery_monitor.py workers

# Health check (returns exit codes for monitoring)
python backend/scripts/celery_monitor.py health-check
```

### Health Check Exit Codes
- `0`: Healthy (< 100 tasks)
- `1`: Warning (100-500 tasks)
- `2`: Critical (> 500 tasks or no workers)

## 📊 Expected Impact

### Before Fixes
- **Task accumulation**: 2,400+ tasks after 8-hour downtime
- **Retry storms**: Failed tasks retrying 3x with exponential backoff
- **Database saturation**: Connection pool exhaustion
- **Stale task execution**: Tasks from hours ago still running

### After Fixes
- **Controlled accumulation**: Max 2 hours of tasks (120-150 tasks)
- **Fast failure**: 1 retry max, 5-minute fixed delay
- **Clean sessions**: Proper database connection management
- **Downtime protection**: Stale tasks automatically skipped

## 🚀 Deployment Recommendations

1. **Deploy during low activity** to minimize disruption
2. **Purge existing queue** before deployment:
   ```bash
   python backend/scripts/celery_monitor.py purge
   ```
3. **Monitor queue health** after deployment:
   ```bash
   python backend/scripts/celery_monitor.py health-check
   ```
4. **Set up monitoring alerts** for queue size > 100 tasks

## 🔧 Configuration Changes

### Celery Beat Schedule (Unchanged)
- `collect-faction-warfare-data`: Every hour
- `orchestrate-killmail-collection`: Every hour  
- `collect-general-warzone-data`: Every hour
- `cleanup-old-data`: Daily
- `health-check`: Every 5 minutes

### Task Timeouts (Unchanged)
- `task_time_limit`: 30 minutes
- `task_soft_time_limit`: 25 minutes

## 🎯 Key Benefits

1. **Prevents queue saturation** during downtime periods
2. **Reduces database load** with minimal retries and proper session handling
3. **Faster recovery** from failures with fixed retry delays
4. **Automatic cleanup** of stale/irrelevant tasks
5. **Better monitoring** with the new management script
6. **Graceful degradation** during worker crashes or restarts

These fixes should resolve the database capacity issues while maintaining reliable data collection functionality.
