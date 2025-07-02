#!/usr/bin/env python3
"""
Celery Beat Scheduler Startup Script

This script starts the Celery beat scheduler for periodic tasks
in the AI Email Assistant system.

Usage:
    python scripts/start_celery_beat.py [--loglevel INFO]
"""

import argparse
import sys
import os
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    """Start Celery beat scheduler"""
    parser = argparse.ArgumentParser(description="Start AI Email Assistant Celery Beat Scheduler")
    parser.add_argument("--loglevel", default="info", choices=["debug", "info", "warning", "error", "critical"])
    parser.add_argument("--schedule-file", default="celerybeat-schedule", help="Path to schedule database file")
    parser.add_argument("--pidfile", default="celerybeat.pid", help="Path to PID file")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Celery beat scheduler...")
    
    try:
        # Import Celery app
        from src.services.background_tasks import celery_app
        
        # Build beat arguments
        beat_args = [
            'beat',
            '--loglevel', args.loglevel,
            '--schedule', args.schedule_file,
            '--pidfile', args.pidfile
        ]
        
        logger.info(f"Starting beat scheduler with args: {' '.join(beat_args)}")
        logger.info(f"Broker: {celery_app.conf.broker_url}")
        logger.info(f"Schedule file: {args.schedule_file}")
        
        # Start beat scheduler
        celery_app.start(beat_args)
        
    except KeyboardInterrupt:
        logger.info("Beat scheduler shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start beat scheduler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()