import logging
import logging.handlers
import os
import sys
import traceback
import asyncio
from pathlib import Path
from typing import Optional
import discord

from settings import admin_user_id

LOG_DIR = "logs"
Path(LOG_DIR).mkdir(exist_ok=True)

class DiscordAlertHandler(logging.Handler):
    """Custom logging handler that sends error alerts to Discord"""

    def __init__(self, level=logging.ERROR):
        super().__init__(level)
        self.bot: Optional[discord.Bot] = None
        self.admin_user_id = admin_user_id
        self.alert_queue = []
        self.processing_alerts = False

    def set_bot(self, bot: discord.Bot):
        """Set the bot instance for sending alerts"""
        self.bot = bot
        # Process any queued alerts
        if self.alert_queue and not self.processing_alerts:
            asyncio.create_task(self._process_alert_queue())

    def emit(self, record):
        """Handle log record and send alert if it's an error"""
        if record.levelno >= logging.ERROR:
            # Create alert data
            alert_data = {
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.name,
                'filename': record.filename,
                'lineno': record.lineno,
                'timestamp': self.format(record),
                'traceback': None
            }

            # Add Discord context from extra fields if available
            for field in ['guild_id', 'guild_name', 'channel_id', 'channel_name', 'user_id', 'user_name', 'command_name']:
                if hasattr(record, field):
                    alert_data[field] = getattr(record, field)

            # Add traceback if available
            if record.exc_info:
                alert_data['traceback'] = ''.join(traceback.format_exception(*record.exc_info))
            elif hasattr(record, 'stack_info') and record.stack_info:
                alert_data['traceback'] = record.stack_info

            # Queue the alert
            self.alert_queue.append(alert_data)

            # Process alerts if bot is available
            if self.bot and not self.processing_alerts:
                asyncio.create_task(self._process_alert_queue())

    async def _process_alert_queue(self):
        """Process queued alerts"""
        if self.processing_alerts or not self.bot:
            return

        self.processing_alerts = True

        try:
            while self.alert_queue:
                alert_data = self.alert_queue.pop(0)
                await self._send_alert(alert_data)
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
        except Exception as e:
            # Avoid infinite recursion by using print instead of logging
            print(f"Error processing alert queue: {e}")
        finally:
            self.processing_alerts = False

    async def _send_alert(self, alert_data: dict):
        """Send individual alert to admin"""
        try:
            admin_user = await self.bot.fetch_user(self.admin_user_id)
            if not admin_user:
                return

            # Create embed for error alert
            embed = discord.Embed(
                title="🚨 Bot Error Alert",
                color=discord.Color.red(),
                description=f"**Level:** {alert_data['level']}\n"
                           f"**Module:** {alert_data['module']}\n"
                           f"**File:** {alert_data['filename']}:{alert_data['lineno']}"
            )

            # Add error message (truncated if too long)
            error_msg = alert_data['message']
            if len(error_msg) > 1024:
                error_msg = error_msg[:1021] + "..."
            embed.add_field(
                name="Error Message",
                value=f"```{error_msg}```",
                inline=False
            )

            if alert_data.get('guild_name'):
                embed.add_field(
                    name="Server",
                    value=f"{alert_data['guild_name']} (ID: {alert_data.get('guild_id', 'Unknown')})",
                    inline=True
                )

            if alert_data.get('channel_name'):
                embed.add_field(
                    name="Channel",
                    value=f"{alert_data['channel_name']} (ID: {alert_data.get('channel_id', 'Unknown')})",
                    inline=True
                )

            if alert_data.get('user_name'):
                embed.add_field(
                    name="User",
                    value=f"{alert_data['user_name']} (ID: {alert_data.get('user_id', 'Unknown')})",
                    inline=True
                )

            embed.add_field(
                name="Time",
                value=alert_data['timestamp'],
                inline=True
            )

            # Handle traceback
            traceback_text = alert_data.get('traceback', '')
            if traceback_text:
                if len(traceback_text) > 1000:
                    # Send traceback as file if it's long
                    traceback_file = discord.File(
                        fp=traceback_text.encode('utf-8'),
                        filename="error_traceback.txt"
                    )
                    await admin_user.send(embed=embed, file=traceback_file)
                else:
                    embed.add_field(
                        name="Traceback",
                        value=f"```python\n{traceback_text[:1000]}```",
                        inline=False
                    )
                    await admin_user.send(embed=embed)
            else:
                await admin_user.send(embed=embed)

        except Exception as e:
            # Avoid infinite recursion by using print instead of logging
            print(f"Failed to send Discord alert: {e}")

# Global alert handler instance
discord_alert_handler = DiscordAlertHandler()

def setup_logging(log_level=None):
    """Initalizes logger."""

    # Get log level from environment variable, fallback to INFO if not set
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, log_level))

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with daily rotation
    file_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "bot.log"),
        when='midnight',
        interval=1,
        backupCount=7,  # Keep 7 days of logs
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # DM alerts.
    if admin_user_id:
        # Add Discord alert handler
        discord_alert_handler.setFormatter(formatter)
        root_logger.addHandler(discord_alert_handler)

    return root_logger

def get_logger(name):
    """Get a logger for a module."""
    return logging.getLogger(name)

def set_bot_for_alerts(bot: discord.Bot):
    """Set the bot instance for Discord alerts"""
    discord_alert_handler.set_bot(bot)
