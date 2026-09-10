import asyncio

import pytest


class FakeProcess:
    def __init__(self, returncode: int = 0, sleep: float | None = None):
        self.returncode = returncode
        self._sleep = sleep
        self.killed = False

    async def communicate(self):
        if self._sleep is not None:
            await asyncio.sleep(self._sleep)
        return b"", b""

    def kill(self):
        self.killed = True


@pytest.fixture
def fake_subprocess(monkeypatch):
    def _install(returncode: int = 0, sleep: float | None = None):
        async def fake_create_subprocess_exec(*args, **kwargs):
            return FakeProcess(returncode=returncode, sleep=sleep)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    return _install
