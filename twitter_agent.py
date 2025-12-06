import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

class TwitterAgent:
    def __init__(self, auth_state_path: str = "auth.json", base_url: str = "https://x.com"):
        self.auth_state_path = auth_state_path
        self.base_url = base_url
        self._playwright: Optional[object] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self):
        if self._browser:
            return

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Usamos la sesión guardada de auth.json
        self._context = await self._browser.new_context(
            storage_state=self.auth_state_path
        )

        self._page = await self._context.new_page()

        try:
            # ⚠️ NO usar networkidle con X/Twitter
            await self._page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            print("Aviso: timeout cargando la página principal, continuamos de todos modos.")

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def read_last_tweets(self, username: str, count: int = 5) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{username}"
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except PlaywrightTimeoutError:
            print(f"Aviso: timeout cargando el perfil {url}, continuamos igual.")
        # TODO: interceptar GraphQL para devolver JSON real
        return []

    async def reply_to_tweet(self, tweet_id: str, text: str) -> str:
        # TODO: navegar al tweet y escribir reply
        return f"Reply to {tweet_id} (placeholder)."

    async def post_tweet(self, text: str) -> str:
        # TODO: abrir composer y postear tweet
        return "Tweet posted (placeholder)."

    async def quote_tweet(self, tweet_id: str, comment: str) -> str:
        # TODO: hacer quote-retweet
        return f"Quote tweet to {tweet_id} (placeholder)."