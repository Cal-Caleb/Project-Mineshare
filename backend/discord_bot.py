"""Discord bot entrypoint — run as a separate process."""

import asyncio
import logging

from bot.bot import create_bot, load_cogs
from bot.views import AdminVoteView, UploadApprovalView, VoteView
from core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    settings = get_settings()
    if not settings.discord_bot_token:
        logging.error("DISCORD_BOT_TOKEN not set")
        return

    bot = create_bot()

    # Register persistent views before bot starts so button callbacks work on restart
    bot.add_view(VoteView(vote_id=0))
    bot.add_view(AdminVoteView(vote_id=0))
    bot.add_view(UploadApprovalView(upload_id=0))

    await load_cogs(bot)
    await bot.start(settings.discord_bot_token)


if __name__ == "__main__":
    asyncio.run(main())
