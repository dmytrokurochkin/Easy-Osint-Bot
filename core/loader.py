from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp.resolver import ThreadedResolver

from core.config import Config

# aiodns (pulled in transitively by maigret/holehe) makes aiohttp default to
# its c-ares-based AsyncResolver for every connection in this process,
# including the bot's own Telegram API calls. On Windows that resolver
# frequently fails to read the OS's real DNS config ("Could not contact DNS
# servers") even though the machine is otherwise online. Force the reliable
# stdlib-based resolver for the bot's own session instead.


def create_bot(config: Config) -> Bot:
    session = AiohttpSession()
    session._connector_init["resolver"] = ThreadedResolver()
    return Bot(token=config.bot_token, session=session)


def create_dispatcher() -> Dispatcher:
    return Dispatcher()
