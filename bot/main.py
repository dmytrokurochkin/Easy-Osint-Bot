import asyncio
import logging

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.config import load_config
from bot.db import init_db
from bot.handlers import admin, search, start


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    config = load_config()

    conn = await init_db("data/bot.sqlite3")
    bot = Bot(token=config.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(start.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(search.router)

    try:
        await dispatcher.start_polling(
            bot,
            conn=conn,
            admin_id=config.admin_id,
            blackbird_dir=config.blackbird_dir,
        )
    finally:
        await conn.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
