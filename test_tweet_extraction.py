#!/usr/bin/env python3
"""
Test script for debugging tweet extraction.

This script helps diagnose issues with reading tweets by:
1. Opening the browser visibly
2. Navigating to a profile
3. Showing detailed logs
4. Saving screenshots and HTML for inspection
"""

import asyncio
import sys
from src.infrastructure.browser_manager import BrowserManager
from src.infrastructure.twitter_repository import PlaywrightTwitterRepository
from src.infrastructure.logging_config import setup_logging
from src.domain.use_cases import ReadLastTweetsUseCase


async def test_tweet_extraction(username: str = "elonmusk", count: int = 5):
    """
    Test tweet extraction with detailed debugging.

    Args:
        username: Twitter username to test
        count: Number of tweets to extract
    """
    # Setup logging with DEBUG level
    setup_logging("DEBUG")

    print("=" * 70)
    print(f"Testing Tweet Extraction for @{username}")
    print("=" * 70)
    print()

    browser = None
    try:
        # Initialize browser (will be visible since we'll override config)
        print("1. Starting browser...")
        browser = BrowserManager()

        # Force non-headless for debugging
        from src.config import config
        original_headless = config.BROWSER_HEADLESS
        config.BROWSER_HEADLESS = False

        await browser.start()
        print("   ✓ Browser started (visible mode for debugging)")
        print()

        # Initialize repository and use case
        print("2. Initializing Twitter repository...")
        repo = PlaywrightTwitterRepository(browser)
        use_case = ReadLastTweetsUseCase(repo)
        print("   ✓ Repository initialized")
        print()

        # Navigate and extract
        print(f"3. Navigating to https://x.com/{username}")
        print(f"   This will:")
        print(f"   - Navigate to the profile")
        print(f"   - Wait for tweets to load")
        print(f"   - Scroll to trigger loading")
        print(f"   - Extract tweet data")
        print()
        print("   Watch the browser window to see what's happening...")
        print()

        tweets = await use_case.execute(username, count)

        print()
        print("=" * 70)
        print(f"Results: Extracted {len(tweets)} tweets")
        print("=" * 70)
        print()

        if tweets:
            for i, tweet in enumerate(tweets, 1):
                print(f"Tweet {i}:")
                print(f"  ID: {tweet.id}")
                print(f"  Text: {tweet.text[:100]}{'...' if len(tweet.text) > 100 else ''}")
                print(f"  URL: {tweet.url}")
                print()
        else:
            print("⚠ No tweets extracted!")
            print()
            print("Debugging steps:")
            print("1. Check if 'debug_no_tweets.png' was created")
            print("2. Look at the browser window - do you see tweets?")
            print("3. Check the logs above for errors")
            print("4. Try a different username (e.g., 'twitter' or 'X')")
            print()
            print("Common issues:")
            print("- Authentication expired: run 'python login_and_save_auth.py'")
            print("- Twitter DOM changed: update selectors in twitter_repository.py")
            print("- Page not fully loaded: increase wait time")
            print()

        # Keep browser open for inspection
        print("=" * 70)
        print("Browser will stay open for 10 seconds for inspection...")
        print("Press Ctrl+C to close immediately")
        print("=" * 70)
        await asyncio.sleep(10)

        # Restore original headless setting
        config.BROWSER_HEADLESS = original_headless

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if browser:
            print("\nCleaning up...")
            await browser.stop()
            print("✓ Browser closed")


def main():
    """Main entry point."""
    username = sys.argv[1] if len(sys.argv) > 1 else "elonmusk"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"Testing with username: @{username}, count: {count}")
    print("(You can override: python test_tweet_extraction.py <username> <count>)")
    print()

    asyncio.run(test_tweet_extraction(username, count))


if __name__ == "__main__":
    main()
