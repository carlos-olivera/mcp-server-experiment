"""Playwright-based implementation of Twitter operations."""

import logging
import asyncio
import re
from typing import List, Optional
from datetime import datetime
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from src.domain.interfaces import ITwitterRepository, TwitterRepositoryError
from src.domain.models import Tweet, ActionResult, TweetPostResult, ReplyResult
from src.infrastructure.browser_manager import BrowserManager
from src.config import config

logger = logging.getLogger(__name__)


class PlaywrightTwitterRepository(ITwitterRepository):
    """
    Playwright-based implementation of Twitter repository.

    Uses web scraping and DOM manipulation to interact with Twitter.
    """

    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self._timeout = config.BROWSER_TIMEOUT

    async def read_last_tweets(self, username: str, count: int) -> List[Tweet]:
        """
        Read the last N tweets from a user's profile.

        This implementation:
        1. Navigates to the user's profile
        2. Waits for tweets to appear
        3. Scrolls to load more if needed
        4. Extracts tweet data from the DOM
        """
        logger.info(f"Reading last {count} tweets from @{username}")

        page = self.browser_manager.get_page()
        url = f"{config.TWITTER_BASE_URL}/{username}"

        try:
            # Navigate to user profile
            logger.debug(f"Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=self._timeout)

            # Wait for tweets container to appear
            # Twitter's timeline uses this selector
            try:
                await page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                logger.debug("Tweet container found")
            except PlaywrightTimeoutError:
                logger.warning("No tweets found on page - user may have no tweets or page structure changed")
                return []

            # Give additional time for initial tweets to render
            await asyncio.sleep(3)

            # Scroll down a bit to trigger loading more tweets
            for _ in range(2):
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)

            # Extract tweets from the page
            tweets = await self._extract_tweets_from_page(page, count, username)

            logger.info(f"Successfully extracted {len(tweets)} tweets from @{username}")
            return tweets

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout loading profile @{username}: {e}")
            raise TwitterRepositoryError(
                f"Timeout loading profile @{username}",
                error_code="TIMEOUT"
            )
        except Exception as e:
            logger.error(f"Error reading tweets from @{username}: {e}")
            raise TwitterRepositoryError(
                f"Failed to read tweets: {str(e)}",
                error_code="READ_FAILED"
            )

    async def reply_to_tweet(self, tweet_id: str, text: str) -> ReplyResult:
        """
        Reply to a tweet by navigating to it and using the reply button.

        This implementation:
        1. Navigates to the tweet
        2. Clicks the reply button
        3. Fills in the reply text
        4. Submits the reply
        """
        logger.info(f"Replying to tweet {tweet_id}")

        page = self.browser_manager.get_page()
        tweet_url = f"{config.TWITTER_BASE_URL}/i/status/{tweet_id}"

        try:
            # Navigate to tweet
            logger.debug(f"Navigating to tweet: {tweet_url}")
            await page.goto(tweet_url, wait_until="domcontentloaded", timeout=self._timeout)
            await asyncio.sleep(2)

            # Find and click reply button
            # Twitter uses data-testid="reply" for reply buttons
            reply_button = page.locator('[data-testid="reply"]').first
            await reply_button.click(timeout=5000)
            logger.debug("Clicked reply button")

            await asyncio.sleep(1)

            # Find the tweet composer and type the reply
            # Twitter uses data-testid="tweetTextarea_0" for the main composer
            composer = page.locator('[data-testid="tweetTextarea_0"]').first
            await composer.fill(text)
            logger.debug("Filled reply text")

            await asyncio.sleep(0.5)

            # Click the reply submit button
            # Twitter uses data-testid="tweetButton" or "tweetButtonInline"
            send_button = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first
            await send_button.click(timeout=5000)
            logger.debug("Clicked send button")

            # Wait for the reply to be posted
            await asyncio.sleep(2)

            logger.info(f"Successfully replied to tweet {tweet_id}")

            return ReplyResult(
                success=True,
                message=f"Successfully replied to tweet {tweet_id}",
                original_tweet_id=tweet_id,
                data={"reply_text": text}
            )

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout replying to tweet {tweet_id}: {e}")
            raise TwitterRepositoryError(
                f"Timeout replying to tweet {tweet_id}",
                error_code="TIMEOUT"
            )
        except Exception as e:
            logger.error(f"Error replying to tweet {tweet_id}: {e}")
            raise TwitterRepositoryError(
                f"Failed to reply: {str(e)}",
                error_code="REPLY_FAILED"
            )

    async def retweet(self, tweet_id: str) -> ActionResult:
        """
        Retweet a tweet.

        This implementation:
        1. Navigates to the tweet
        2. Clicks the retweet button
        3. Confirms the retweet
        """
        logger.info(f"Retweeting tweet {tweet_id}")

        page = self.browser_manager.get_page()
        tweet_url = f"{config.TWITTER_BASE_URL}/i/status/{tweet_id}"

        try:
            # Navigate to tweet
            logger.debug(f"Navigating to tweet: {tweet_url}")
            await page.goto(tweet_url, wait_until="domcontentloaded", timeout=self._timeout)
            await asyncio.sleep(2)

            # Find and click retweet button
            # Twitter uses data-testid="retweet" for retweet buttons
            retweet_button = page.locator('[data-testid="retweet"]').first
            await retweet_button.click(timeout=5000)
            logger.debug("Clicked retweet button")

            await asyncio.sleep(0.5)

            # Confirm retweet in the popup menu
            # Twitter shows a menu with data-testid="retweetConfirm"
            confirm_button = page.locator('[data-testid="retweetConfirm"]').first
            await confirm_button.click(timeout=5000)
            logger.debug("Clicked confirm button")

            await asyncio.sleep(1)

            logger.info(f"Successfully retweeted tweet {tweet_id}")

            return ActionResult(
                success=True,
                message=f"Successfully retweeted tweet {tweet_id}",
                data={"tweet_id": tweet_id}
            )

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout retweeting tweet {tweet_id}: {e}")
            raise TwitterRepositoryError(
                f"Timeout retweeting tweet {tweet_id}",
                error_code="TIMEOUT"
            )
        except Exception as e:
            logger.error(f"Error retweeting tweet {tweet_id}: {e}")
            raise TwitterRepositoryError(
                f"Failed to retweet: {str(e)}",
                error_code="RETWEET_FAILED"
            )

    async def post_tweet(self, text: str) -> TweetPostResult:
        """
        Post a new tweet.

        This implementation:
        1. Navigates to Twitter home
        2. Finds the tweet composer
        3. Types the text
        4. Clicks the post button
        """
        logger.info("Posting new tweet")

        page = self.browser_manager.get_page()

        try:
            # Navigate to home to ensure we're in the right place
            logger.debug(f"Navigating to {config.TWITTER_BASE_URL}/home")
            await page.goto(f"{config.TWITTER_BASE_URL}/home", wait_until="domcontentloaded", timeout=self._timeout)
            await asyncio.sleep(2)

            # Find the tweet composer (main one on the home page)
            # Twitter uses data-testid="tweetTextarea_0" for the main composer
            composer = page.locator('[data-testid="tweetTextarea_0"]').first
            await composer.click(timeout=5000)
            await composer.fill(text)
            logger.debug("Filled tweet text")

            await asyncio.sleep(0.5)

            # Click the post button
            # Twitter uses data-testid="tweetButtonInline" or "tweetButton"
            post_button = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first
            await post_button.click(timeout=5000)
            logger.debug("Clicked post button")

            # Wait for tweet to be posted
            await asyncio.sleep(2)

            logger.info("Successfully posted tweet")

            return TweetPostResult(
                success=True,
                message="Successfully posted tweet",
                data={"tweet_text": text}
            )

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout posting tweet: {e}")
            raise TwitterRepositoryError(
                "Timeout posting tweet",
                error_code="TIMEOUT"
            )
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            raise TwitterRepositoryError(
                f"Failed to post tweet: {str(e)}",
                error_code="POST_FAILED"
            )

    async def _extract_tweets_from_page(self, page: Page, count: int, username: str) -> List[Tweet]:
        """
        Extract tweet data from the loaded page.

        This implementation:
        - Finds all tweet article elements
        - Extracts text content and metadata
        - Handles various tweet formats
        - Returns structured Tweet objects
        """
        tweets = []

        try:
            # Twitter uses article[data-testid="tweet"] for tweet containers
            tweet_elements = await page.locator('article[data-testid="tweet"]').all()

            logger.debug(f"Found {len(tweet_elements)} tweet elements on page")

            if len(tweet_elements) == 0:
                logger.warning("No tweet elements found - page structure may have changed")
                # Save screenshot for debugging if needed
                try:
                    await page.screenshot(path="debug_no_tweets.png")
                    logger.debug("Screenshot saved to debug_no_tweets.png")
                except:
                    pass

            for i, element in enumerate(tweet_elements[:count]):
                try:
                    # Extract tweet text - Twitter uses div[data-testid="tweetText"] or [lang] attribute
                    text = ""

                    # Try multiple selectors for tweet text
                    text_selectors = [
                        '[data-testid="tweetText"]',
                        'div[lang]',  # Tweet text often has lang attribute
                        'div[dir="auto"][lang]'
                    ]

                    for selector in text_selectors:
                        text_element = element.locator(selector).first
                        if await text_element.count() > 0:
                            text = await text_element.inner_text()
                            if text:
                                break

                    if not text:
                        logger.debug(f"Tweet {i}: No text found, trying alternative extraction")
                        # Fallback: get all text content
                        text = await element.inner_text()
                        # Clean up the text (remove timestamps, etc.)
                        text = text.split('\n')[0] if text else ""

                    # Extract tweet link to get ID
                    # Links in tweets have format /username/status/TWEET_ID
                    tweet_id = ""
                    href = ""

                    # Try to find the status link
                    link_elements = await element.locator('a[href*="/status/"]').all()

                    for link in link_elements:
                        href = await link.get_attribute("href")
                        if href:
                            match = re.search(r'/status/(\d+)', href)
                            if match:
                                tweet_id = match.group(1)
                                break

                    # Log what we found
                    logger.debug(f"Tweet {i}: text_length={len(text)}, id={tweet_id}, href={href}")

                    # Only add tweet if we have both text and ID
                    if text and tweet_id:
                        tweet = Tweet(
                            id=tweet_id,
                            text=text.strip(),
                            author_username=username,
                            url=f"{config.TWITTER_BASE_URL}/{username}/status/{tweet_id}",
                            created_at=datetime.now()  # Placeholder - would need proper parsing
                        )
                        tweets.append(tweet)
                        logger.info(f"Extracted tweet {tweet_id}: {text[:80]}...")
                    else:
                        logger.warning(f"Tweet {i}: Skipping - missing text={not text} or id={not tweet_id}")

                except Exception as e:
                    logger.warning(f"Failed to extract tweet {i}: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error extracting tweets from page: {e}", exc_info=True)

        logger.info(f"Successfully extracted {len(tweets)} out of requested {count} tweets")
        return tweets
