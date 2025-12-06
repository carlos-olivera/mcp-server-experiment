"""Browser lifecycle management for Playwright."""

import logging
from typing import Optional
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    Playwright
)
from src.config import config

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser lifecycle and provides reusable browser instances."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_started = False

    async def start(self) -> None:
        """
        Start the browser and load the Twitter session.

        Raises:
            RuntimeError: If browser is already started
            FileNotFoundError: If auth.json doesn't exist
        """
        if self._is_started:
            logger.warning("Browser is already started")
            return

        logger.info("Starting browser manager")

        try:
            # Validate auth file exists
            config.validate()

            # Start Playwright
            self._playwright = await async_playwright().start()
            logger.debug("Playwright started")

            # Launch browser
            self._browser = await self._playwright.chromium.launch(
                headless=config.BROWSER_HEADLESS,
                args=["--disable-blink-features=AutomationControlled"],
            )
            logger.debug(f"Browser launched (headless={config.BROWSER_HEADLESS})")

            # Create context with saved authentication
            self._context = await self._browser.new_context(
                storage_state=str(config.get_auth_state_path())
            )
            logger.debug("Browser context created with authentication")

            # Create initial page
            self._page = await self._context.new_page()
            logger.debug("Initial page created")

            # Navigate to Twitter (don't wait for networkidle as Twitter constantly loads)
            try:
                await self._page.goto(
                    config.TWITTER_BASE_URL,
                    wait_until="domcontentloaded",
                    timeout=config.BROWSER_TIMEOUT
                )
                logger.info(f"Navigated to {config.TWITTER_BASE_URL}")
            except PlaywrightTimeoutError:
                logger.warning("Timeout loading Twitter homepage, continuing anyway")

            self._is_started = True
            logger.info("Browser manager started successfully")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the browser and clean up resources."""
        logger.info("Stopping browser manager")

        try:
            if self._context:
                await self._context.close()
                logger.debug("Browser context closed")

            if self._browser:
                await self._browser.close()
                logger.debug("Browser closed")

            if self._playwright:
                await self._playwright.stop()
                logger.debug("Playwright stopped")

        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")

        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._is_started = False
            logger.info("Browser manager stopped")

    def get_page(self) -> Page:
        """
        Get the current page instance.

        Returns:
            The active page

        Raises:
            RuntimeError: If browser is not started
        """
        if not self._is_started or not self._page:
            raise RuntimeError("Browser is not started. Call start() first.")
        return self._page

    def is_started(self) -> bool:
        """Check if the browser is currently started."""
        return self._is_started

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
