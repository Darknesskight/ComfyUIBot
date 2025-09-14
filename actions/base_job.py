from collections.abc import Coroutine
import io
import json
import logging
import asyncio
import time
from enum import Enum
from api.websocket_subsystem import add_client, remove_client, is_websocket_connected
from api.comfy_api import get_history, queue_prompt, get_image
from api.job_tracker import job_tracker

logger = logging.getLogger(__name__)


class Status(Enum):
    READY = 1
    QUEUED = 2
    RUNNING = 3
    IMAGE_READY = 4
    DONE = 5


class BaseJob:
    """Base class for all job types"""

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.state = Status.READY
        self._registered = False

    async def run(self):
        """Main execution flow for the job"""
        logger.info("Job starting")

        # Register job with tracker
        await job_tracker.register_job(self, self.progress_callback)
        self._registered = True

        try:
            self.state = Status.RUNNING
            result = await self.execute()
            self.state = Status.DONE
            return result
        except Exception as e:
            logger.error(f"Error in job.run(): {e}")
            raise
        finally:
            # Unregister job with tracker
            if self._registered:
                await job_tracker.unregister_job(self)

    async def execute(self):
        """Override this method in subclasses to implement job-specific logic"""
        raise NotImplementedError("Subclasses must implement execute method")


class ComfyJob(BaseJob):
    """Base class for all ComfyUI job types"""

    def __init__(self, prompt, progress_callback=None):
        super().__init__(progress_callback)
        self.prompt = prompt
        self.prompt_id = -1
        self.msg = None
        self.last_update = time.time()
        self.progress_image = None

    async def execute(self):
        """Main execution flow for ComfyUI jobs"""
        logger.info(f"ComfyUI job starting for prompt_id: {self.prompt_id}")

        # Check if websocket is connected before proceeding
        if not is_websocket_connected():
            logger.error("Websocket is not connected, cannot process image generation")
            raise RuntimeError("Websocket connection not available")

        await add_client(self)
        try:
            logger.info("Sending prompt to ComfyUI")
            await self.send_prompt()
            logger.info(f"Prompt sent, waiting for image. Prompt ID: {self.prompt_id}")
            await self.wait_for_image()
            logger.info("Image generation completed, retrieving images")
            return await self.get_images()
        except Exception as e:
            logger.error(f"Error in ComfyJob.execute(): {e}")
            raise
        finally:
            await remove_client(self)

    async def wait_for_image(self):
        """Wait for image generation to complete"""
        while self.state != Status.IMAGE_READY:
            await asyncio.sleep(0.5)

    async def send_prompt(self):
        """Send prompt to ComfyUI queue"""
        try:
            logger.info(f"Queueing prompt: {self.prompt}")
            prompt_id = await queue_prompt(self.prompt)
            self.prompt_id = prompt_id["prompt_id"]
            self.state = Status.QUEUED
            logger.info(f"Prompt queued successfully with ID: {self.prompt_id}")
        except Exception as e:
            logger.error(f"Failed to queue prompt: {e}")
            raise

    async def on_message(self, ws_message):
        """Handle websocket messages"""
        # Ignore all messages if we are not running.
        if self.state != Status.QUEUED and self.state != Status.RUNNING:
            return

        logger.debug(f"Received websocket message: {type(ws_message)}")

        # Handle preview image.
        if isinstance(ws_message, bytes) and self.state == Status.RUNNING:
            image_buffer = ws_message[8:]
            self.progress_image = io.BytesIO(image_buffer)
            logger.debug("Received preview image")

        # Handle normal messages
        if isinstance(ws_message, str):
            try:
                message = json.loads(ws_message)
                data = message["data"]
                logger.debug(f"Processing message type: {message.get('type', 'unknown')}")

                if message["type"] == "execution_start":
                    await self.on_execution_start(data)

                if message["type"] == "executing":
                    await self.on_executing(data)

                if message["type"] == "progress":
                    await self.on_progress(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse websocket message: {e}")
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")

    async def on_execution_start(self, data):
        """Handle execution start message"""
        if data["prompt_id"] != self.prompt_id:
            return
        logger.info(f"Execution started for prompt {self.prompt_id}")
        self.state = Status.RUNNING

    async def on_progress(self, data):
        """Handle progress updates"""
        if self.state != Status.RUNNING:
            return

        # Rate limiting - only update every 0.5 seconds to prevent spam while staying responsive
        current_time = time.time()
        if current_time - self.last_update < 0.5:
            return

        self.last_update = current_time

        # Only call progress callback if it exists
        if self.progress_callback:
            await self.progress_callback(data["value"] / data["max"], self.progress_image)

    async def on_executing(self, data):
        """Handle executing node message"""
        if data["prompt_id"] != self.prompt_id:
            return
        logger.debug(f"Executing node {data.get('node', 'unknown')} for prompt {self.prompt_id}")
        if data["node"] is None:
            logger.info(f"Execution completed for prompt {self.prompt_id}")
            if self.progress_callback:
                await self.progress_callback(1, self.progress_image)
            self.state = Status.IMAGE_READY

    async def get_images(self):
        """Retrieve generated images from ComfyUI"""
        try:
            logger.info(f"Retrieving images for prompt {self.prompt_id}")
            output_images = {}
            history = await get_history(self.prompt_id)
            history_data = history[self.prompt_id]
            
            for node_id in history_data["outputs"]:
                node_output = history_data["outputs"][node_id]
                if "images" in node_output:
                    images_output = []
                    for image in node_output["images"]:
                        logger.debug(f"Getting image: {image}")
                        image_data = await get_image(
                            image["filename"], image["subfolder"], image["type"]
                        )
                        images_output.append(image_data)
                    output_images[node_id] = images_output
            
            logger.info(f"Retrieved {len(output_images)} output nodes with images")
            return output_images
        except Exception as e:
            logger.error(f"Failed to get images: {e}")
            raise


class ReplicateJob(BaseJob):
    """Job class for Replicate-based tasks (Flux, Video, etc.)"""

    def __init__(self, task_func, progress_callback=None):
        super().__init__(progress_callback)
        self.task_func = task_func

    async def execute(self):
        """Execute the replicate task"""
        logger.info("Replicate job executing")
        # For replicate tasks, we don't have progress updates, so we just await the task
        result = await self.task_func()
        return result
