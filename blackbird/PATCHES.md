# Local modifications to vendored blackbird

This directory is vendored from https://github.com/p1ngul1n0/blackbird
(exact upstream commit not recorded at vendoring time). Three local
patches were applied on top of upstream, for Windows compatibility:

1. **`blackbird.py`** — `config.console = Console()` changed to
   `config.console = Console(legacy_windows=False)`. Works around a
   `rich`/Windows crash: when stdout has no real console attached (which
   is exactly how this bot runs it — piped, from a subprocess), rich's
   "legacy Windows console" detection misfires and crashes with a
   `UnicodeEncodeError` on the startup banner's block-drawing characters.

2. **`src/modules/core/username.py`** and **`src/modules/core/email.py`**
   — `aiohttp.ClientSession()` changed to
   `aiohttp.ClientSession(connector=aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver()))`.
   Works around `aiodns`'s c-ares-based `AsyncResolver` (aiohttp's default
   when `aiodns` is importable) failing to contact DNS servers on some
   Windows setups even though the system's plain `socket.getaddrinfo` (used
   by `requests`) resolves fine. See this project's root `CLAUDE.md` §6 for
   the full symptom description ("OK, nothing found" with a clean exit
   being the visible symptom of this bug, not an actual zero-results
   search).

If updating this vendored copy from upstream, re-apply these three
patches — check for the corresponding upstream fix first, in case it has
since been fixed there.
