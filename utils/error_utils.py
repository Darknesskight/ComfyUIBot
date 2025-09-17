import discord
from utils.logging_config import get_logger

logger = get_logger(__name__)


async def handle_interaction_error(
    error: Exception,
    interaction: discord.Interaction,
    context_type: str,
    context_name: str = "unknown",
    custom_id: str = "unknown"
) -> None:
    """
    Handle errors that occur in Discord interactions (commands, views, modals, etc.)

    Args:
        error: The exception that occurred
        interaction: The Discord interaction object
        context_type: Type of interaction (e.g., "command", "view", "modal", "button")
        context_name: Name of the specific component (e.g., command name, class name)
        custom_id: Custom ID of the component if applicable
    """
    # Log the error with context information
    logger.error(
        f"{context_type.title()} interaction error in {context_name}",
        extra={
            'guild_id': interaction.guild.id if interaction.guild else None,
            'guild_name': interaction.guild.name if interaction.guild else 'DM',
            'channel_id': interaction.channel.id if interaction.channel else None,
            'channel_name': getattr(interaction.channel, 'name', 'DM') if interaction.channel else 'DM',
            'user_id': interaction.user.id,
            'user_name': str(interaction.user),
            'context_type': context_type,
            'context_name': context_name,
            'custom_id': custom_id
        },
        exc_info=error
    )

    user_message = get_user_friendly_error_message(error)

    user_ping_message = f"{interaction.user.mention} {user_message}"

    # Send user-friendly error message
    try:
        if interaction.response.is_done():
            await interaction.followup.send(user_ping_message)
        else:
            await interaction.response.send_message(user_ping_message)
    except Exception as send_error:
        logger.error(f"Failed to send error message to user: {send_error}")

def get_user_friendly_error_message(error: Exception) -> str:
    """
    Convert an exception into a user-friendly error message. Not the prettiest but
    it handles most of the common reasons why an error occurs.

    Args:
        error: The exception to convert

    Returns:
        A user-friendly error message string
    """
    original_error = error.original if isinstance(error, discord.ApplicationCommandInvokeError) else error

    if isinstance(original_error, discord.Forbidden):
        return "❌ I don't have permission to perform this action."
    elif isinstance(original_error, discord.NotFound):
        return "❌ The requested resource was not found."
    elif isinstance(original_error, discord.HTTPException):
        if original_error.status == 413:
            return "❌ The file you uploaded is too large."
        elif original_error.status == 429:
            return "❌ Rate limit exceeded. Please try again later."
        else:
            return "❌ A network error occurred. Please try again."
    elif isinstance(original_error, discord.CheckFailure):
        return "❌ You don't have permission to use this command."
    elif "timeout" in str(original_error).lower():
        return "❌ The operation timed out. Please try again."
    elif "connection" in str(original_error).lower():
        return "❌ Connection error. Please try again later."

    # Default generic error message
    return "❌ An unexpected error occurred. Please try again."
