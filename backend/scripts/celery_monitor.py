#!/usr/bin/env python3
"""
Celery monitoring and management script for EVE Wargames.

This script provides utilities to monitor and manage the Celery task queue,
including purging stale tasks and checking queue health.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from celery import Celery
from app.config import settings

# Initialize Celery app for monitoring
celery_app = Celery(
    "eve_wargames_monitor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)


def get_queue_stats():
    """Get statistics about the current task queue."""
    inspect = celery_app.control.inspect()
    
    # Get active tasks
    active_tasks = inspect.active()
    if active_tasks:
        total_active = sum(len(tasks) for tasks in active_tasks.values())
    else:
        total_active = 0
    
    # Get scheduled tasks
    scheduled_tasks = inspect.scheduled()
    if scheduled_tasks:
        total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
    else:
        total_scheduled = 0
    
    # Get reserved tasks
    reserved_tasks = inspect.reserved()
    if reserved_tasks:
        total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())
    else:
        total_reserved = 0
    
    return {
        "active": total_active,
        "scheduled": total_scheduled,
        "reserved": total_reserved,
        "total": total_active + total_scheduled + total_reserved
    }


def purge_all_tasks():
    """Purge all tasks from the queue."""
    try:
        purged = celery_app.control.purge()
        print(f"✅ Purged {purged} tasks from the queue")
        return purged
    except Exception as e:
        print(f"❌ Error purging tasks: {e}")
        return 0


def revoke_stale_tasks(max_age_hours=2):
    """Revoke tasks that are older than the specified age."""
    inspect = celery_app.control.inspect()
    
    # Get all scheduled tasks
    scheduled_tasks = inspect.scheduled()
    if not scheduled_tasks:
        print("No scheduled tasks found")
        return 0
    
    revoked_count = 0
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    for worker, tasks in scheduled_tasks.items():
        for task in tasks:
            # Parse task ETA
            eta_str = task.get('eta')
            if eta_str:
                try:
                    eta = datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
                    if eta < cutoff_time:
                        task_id = task.get('request', {}).get('id')
                        if task_id:
                            celery_app.control.revoke(task_id, terminate=True)
                            revoked_count += 1
                            print(f"🗑️  Revoked stale task {task_id} (scheduled for {eta})")
                except Exception as e:
                    print(f"⚠️  Error processing task {task.get('request', {}).get('id', 'unknown')}: {e}")
    
    print(f"✅ Revoked {revoked_count} stale tasks")
    return revoked_count


def show_worker_status():
    """Show the status of Celery workers."""
    inspect = celery_app.control.inspect()
    
    # Get worker stats
    stats = inspect.stats()
    if not stats:
        print("❌ No workers found or workers are not responding")
        return
    
    print("📊 Worker Status:")
    for worker, worker_stats in stats.items():
        print(f"  🔧 {worker}:")
        print(f"    - Pool: {worker_stats.get('pool', {}).get('max-concurrency', 'unknown')} workers")
        print(f"    - Total tasks: {worker_stats.get('total', {})}")
        print(f"    - Uptime: {worker_stats.get('clock', 'unknown')}")


def main():
    parser = argparse.ArgumentParser(description="Celery monitoring and management tool")
    parser.add_argument("command", choices=[
        "stats", "purge", "revoke-stale", "workers", "health-check"
    ], help="Command to execute")
    parser.add_argument("--max-age", type=int, default=2, 
                       help="Maximum age in hours for stale task revocation (default: 2)")
    
    args = parser.parse_args()
    
    print(f"🚀 EVE Wargames Celery Monitor - {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    if args.command == "stats":
        stats = get_queue_stats()
        print("📈 Queue Statistics:")
        print(f"  Active tasks: {stats['active']}")
        print(f"  Scheduled tasks: {stats['scheduled']}")
        print(f"  Reserved tasks: {stats['reserved']}")
        print(f"  Total tasks: {stats['total']}")
        
        if stats['total'] > 100:
            print("⚠️  WARNING: High task count detected! Consider purging or revoking stale tasks.")
    
    elif args.command == "purge":
        print("🗑️  Purging all tasks from queue...")
        purged = purge_all_tasks()
        
    elif args.command == "revoke-stale":
        print(f"🕐 Revoking tasks older than {args.max_age} hours...")
        revoked = revoke_stale_tasks(args.max_age)
        
    elif args.command == "workers":
        show_worker_status()
        
    elif args.command == "health-check":
        print("🏥 Performing health check...")
        stats = get_queue_stats()
        
        # Check if queue is healthy
        if stats['total'] > 500:
            print("❌ CRITICAL: Queue has too many tasks (>500)")
            exit_code = 2
        elif stats['total'] > 100:
            print("⚠️  WARNING: Queue has many tasks (>100)")
            exit_code = 1
        else:
            print("✅ Queue appears healthy")
            exit_code = 0
        
        # Check worker connectivity
        inspect = celery_app.control.inspect()
        if not inspect.stats():
            print("❌ CRITICAL: No workers responding")
            exit_code = 2
        else:
            print("✅ Workers are responding")
        
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
