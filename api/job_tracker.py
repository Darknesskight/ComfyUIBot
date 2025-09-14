import asyncio
from typing import Set, Dict
from utils.logging_config import get_logger

logger = get_logger(__name__)

class JobTracker:
    def __init__(self):
        self.active_jobs: Dict = {}  # job -> progress_callback mapping
        self.lock = asyncio.Lock()

    async def register_job(self, job, progress_callback=None):
        async with self.lock:
            self.active_jobs[job] = progress_callback
        logger.debug(f"Job registered. Active jobs: {len(self.active_jobs)}")

    async def unregister_job(self, job):
        async with self.lock:
            self.active_jobs.pop(job, None)
        logger.debug(f"Job unregistered. Active jobs: {len(self.active_jobs)}")

    def get_active_job_count(self):
        return len(self.active_jobs)

    async def notify_channels(self, message):
        """Send message to all channels with active jobs"""
        channels = set()
        async with self.lock:
            for progress_callback in self.active_jobs.values():
                # Extract channel from ProgressMessenger
                if (hasattr(progress_callback, '__self__') and
                    hasattr(progress_callback.__self__, 'channel')):
                    channels.add(progress_callback.__self__.channel)

        logger.info(f"Sending notification to {len(channels)} channels")
        for channel in channels:
            try:
                await channel.send(message)
            except Exception as e:
                logger.error(f"Failed to send message to channel: {e}")

job_tracker = JobTracker()
