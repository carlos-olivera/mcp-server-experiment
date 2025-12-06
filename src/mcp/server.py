"""MCP server implementation using fastmcp."""

import logging
from typing import List, Dict, Any
from fastmcp import FastMCP
from src.config import config
from src.infrastructure.logging_config import setup_logging
from src.infrastructure.browser_manager import BrowserManager
from src.infrastructure.twitter_repository import PlaywrightTwitterRepository
from src.domain.use_cases import (
    ReadLastTweetsUseCase,
    ReplyToTweetUseCase,
    RetweetUseCase,
    PostTweetUseCase
)
from src.domain.interfaces import TwitterRepositoryError

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(config.MCP_SERVER_NAME)

# Global instances (will be initialized in lifespan)
browser_manager: BrowserManager = None
twitter_repo: PlaywrightTwitterRepository = None
read_tweets_uc: ReadLastTweetsUseCase = None
reply_uc: ReplyToTweetUseCase = None
retweet_uc: RetweetUseCase = None
post_tweet_uc: PostTweetUseCase = None


@mcp.tool()
async def read_last_tweets(username: str, count: int = 5) -> List[Dict[str, Any]]:
    """
    Read the last N tweets from a user's profile.

    Args:
        username: Twitter username (without @)
        count: Number of tweets to retrieve (default: 5, max: 100)

    Returns:
        List of tweet dictionaries with id, text, author, url, etc.

    Example:
        read_last_tweets("elonmusk", 10)
    """
    logger.info(f"MCP tool called: read_last_tweets(@{username}, count={count})")

    try:
        tweets = await read_tweets_uc.execute(username.lstrip('@'), count)
        result = [tweet.to_dict() for tweet in tweets]
        logger.info(f"MCP tool completed: read_last_tweets returned {len(result)} tweets")
        return result

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error in read_last_tweets: {e.message}")
        raise Exception(f"Twitter error: {e.message}")
    except ValueError as e:
        logger.error(f"Validation error in read_last_tweets: {e}")
        raise Exception(f"Validation error: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error in read_last_tweets: {e}")
        raise


@mcp.tool()
async def reply_to_tweet(tweet_id: str, text: str) -> Dict[str, Any]:
    """
    Reply to a tweet.

    Args:
        tweet_id: The ID of the tweet to reply to
        text: The reply text (max 280 characters)

    Returns:
        Dictionary with success status and reply metadata

    Example:
        reply_to_tweet("1234567890", "Great point!")
    """
    logger.info(f"MCP tool called: reply_to_tweet({tweet_id})")

    try:
        result = await reply_uc.execute(tweet_id, text)
        response = result.to_dict()
        logger.info(f"MCP tool completed: reply_to_tweet success={result.success}")
        return response

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error in reply_to_tweet: {e.message}")
        raise Exception(f"Twitter error: {e.message}")
    except ValueError as e:
        logger.error(f"Validation error in reply_to_tweet: {e}")
        raise Exception(f"Validation error: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error in reply_to_tweet: {e}")
        raise


@mcp.tool()
async def retweet(tweet_id: str) -> Dict[str, Any]:
    """
    Retweet (repost) a tweet.

    Args:
        tweet_id: The ID of the tweet to retweet

    Returns:
        Dictionary with success status

    Example:
        retweet("1234567890")
    """
    logger.info(f"MCP tool called: retweet({tweet_id})")

    try:
        result = await retweet_uc.execute(tweet_id)
        response = result.to_dict()
        logger.info(f"MCP tool completed: retweet success={result.success}")
        return response

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error in retweet: {e.message}")
        raise Exception(f"Twitter error: {e.message}")
    except Exception as e:
        logger.exception(f"Unexpected error in retweet: {e}")
        raise


@mcp.tool()
async def post_tweet(text: str) -> Dict[str, Any]:
    """
    Post a new tweet.

    Args:
        text: The tweet text (max 280 characters)

    Returns:
        Dictionary with success status and tweet metadata

    Example:
        post_tweet("Hello, world!")
    """
    logger.info("MCP tool called: post_tweet")

    try:
        result = await post_tweet_uc.execute(text)
        response = result.to_dict()
        logger.info(f"MCP tool completed: post_tweet success={result.success}")
        return response

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error in post_tweet: {e.message}")
        raise Exception(f"Twitter error: {e.message}")
    except ValueError as e:
        logger.error(f"Validation error in post_tweet: {e}")
        raise Exception(f"Validation error: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error in post_tweet: {e}")
        raise


async def initialize_mcp_server():
    """Initialize MCP server with dependencies."""
    global browser_manager, twitter_repo
    global read_tweets_uc, reply_uc, retweet_uc, post_tweet_uc

    logger.info("Initializing MCP server")

    # Setup logging
    setup_logging()

    # Initialize browser manager
    browser_manager = BrowserManager()
    await browser_manager.start()
    logger.info("Browser manager started")

    # Initialize Twitter repository
    twitter_repo = PlaywrightTwitterRepository(browser_manager)
    logger.info("Twitter repository initialized")

    # Initialize use cases
    read_tweets_uc = ReadLastTweetsUseCase(twitter_repo)
    reply_uc = ReplyToTweetUseCase(twitter_repo)
    retweet_uc = RetweetUseCase(twitter_repo)
    post_tweet_uc = PostTweetUseCase(twitter_repo)
    logger.info("Use cases initialized")

    logger.info("MCP server initialization complete")


async def cleanup_mcp_server():
    """Cleanup MCP server resources."""
    global browser_manager

    logger.info("Cleaning up MCP server")

    if browser_manager:
        await browser_manager.stop()
        logger.info("Browser manager stopped")

    logger.info("MCP server cleanup complete")


# Note: fastmcp handles the actual server lifecycle.
# For standalone usage, you would run: mcp.run()
# But this can also be integrated into other frameworks.
