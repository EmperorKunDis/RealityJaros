#!/usr/bin/env python3
"""
Celery Worker Startup Script

This script starts a Celery worker process for handling background tasks
in the AI Email Assistant system.

Usage:
    python scripts/start_celery_worker.py [--concurrency N] [--loglevel INFO]
"""

import argparse
import sys
import os
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    """Start Celery worker"""
    parser = argparse.ArgumentParser(description="Start AI Email Assistant Celery Worker")
    parser.add_argument("--concurrency", type=int, default=4, help="Number of concurrent worker processes")
    parser.add_argument("--loglevel", default="info", choices=["debug", "info", "warning", "error", "critical"])
    parser.add_argument("--queues", default="default", help="Comma-separated list of queues to consume")
    parser.add_argument("--pool", default="prefork", choices=["prefork", "eventlet", "gevent", "solo"])
    parser.add_argument("--autoscale", help="Enable autoscaling (e.g., '10,3' for max 10, min 3)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Celery worker...")
    
    try:
        # Import Celery app
        from src.services.background_tasks import celery_app
        
        # Build worker arguments
        worker_args = [
            'worker',
            '--loglevel', args.loglevel,
            '--queues', args.queues,
            '--pool', args.pool
        ]
        
        if args.autoscale:
            worker_args.extend(['--autoscale', args.autoscale])
        else:
            worker_args.extend(['--concurrency', str(args.concurrency)])
        
        logger.info(f"Starting worker with args: {' '.join(worker_args)}")
        logger.info(f"Broker: {celery_app.conf.broker_url}")
        logger.info(f"Backend: {celery_app.conf.result_backend}")
        
        # Start worker
        celery_app.worker_main(worker_args)
        
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()