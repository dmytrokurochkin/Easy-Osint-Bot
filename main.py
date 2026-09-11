import asyncio
import logging

from dotenv import load_dotenv

from core.config import load_config
from core.loader import create_bot, create_dispatcher
from database import init_db
from handlers.admin import admin_router
from handlers.search import search_router
from handlers.start import start_router
from middlewares.auth import AuthMiddleware


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    config = load_config()

    conn = await init_db("data/bot.sqlite3")
    bot = create_bot(config)
    dispatcher = create_dispatcher()

    # Re-check whitelist/admin authorization on every request, not just
    # /start - see middlewares/auth.py::AuthMiddleware for why this is
    # required (old main-menu messages keep working buttons forever).
    auth_middleware = AuthMiddleware()
    for router in (start_router, admin_router, search_router):
        router.message.outer_middleware(auth_middleware)
        router.callback_query.outer_middleware(auth_middleware)

    dispatcher.include_router(start_router)
    dispatcher.include_router(admin_router)
    dispatcher.include_router(search_router)

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
