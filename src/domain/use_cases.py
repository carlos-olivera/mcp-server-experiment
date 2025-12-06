"""Domain use cases - orchestrate business logic without framework dependencies."""

import logging
from typing import List
from src.domain.interfaces import ITwitterRepository, TwitterRepositoryError
from src.domain.models import Tweet, ActionResult, TweetPostResult, ReplyResult

logger = logging.getLogger(__name__)


class ReadLastTweetsUseCase:
    """Use case for reading the last tweets from a user."""

    def __init__(self, twitter_repo: ITwitterRepository):
        self.twitter_repo = twitter_repo

    async def execute(self, username: str, count: int = 5) -> List[Tweet]:
        """
        Execute the use case to read last tweets.

        Args:
            username: Twitter username (without @)
            count: Number of tweets to retrieve (default: 5)

        Returns:
            List of Tweet objects

        Raises:
            TwitterRepositoryError: If the operation fails
        """
        logger.info(f"Reading last {count} tweets from @{username}")

        if count < 1:
            raise ValueError("Count must be at least 1")
        if count > 100:
            raise ValueError("Count cannot exceed 100")

        try:
            tweets = await self.twitter_repo.read_last_tweets(username, count)
            logger.info(f"Successfully retrieved {len(tweets)} tweets from @{username}")
            return tweets
        except TwitterRepositoryError as e:
            logger.error(f"Failed to read tweets from @{username}: {e.message}")
            raise


class ReplyToTweetUseCase:
    """Use case for replying to a tweet."""

    def __init__(self, twitter_repo: ITwitterRepository):
        self.twitter_repo = twitter_repo

    async def execute(self, tweet_id: str, text: str) -> ReplyResult:
        """
        Execute the use case to reply to a tweet.

        Args:
            tweet_id: The ID of the tweet to reply to
            text: The reply text

        Returns:
            ReplyResult with success status and metadata

        Raises:
            TwitterRepositoryError: If the operation fails
        """
        logger.info(f"Replying to tweet {tweet_id}")

        if not text or not text.strip():
            raise ValueError("Reply text cannot be empty")
        if len(text) > 280:
            raise ValueError("Reply text cannot exceed 280 characters")

        try:
            result = await self.twitter_repo.reply_to_tweet(tweet_id, text)
            logger.info(f"Successfully replied to tweet {tweet_id}")
            return result
        except TwitterRepositoryError as e:
            logger.error(f"Failed to reply to tweet {tweet_id}: {e.message}")
            raise


class RetweetUseCase:
    """Use case for retweeting a tweet."""

    def __init__(self, twitter_repo: ITwitterRepository):
        self.twitter_repo = twitter_repo

    async def execute(self, tweet_id: str) -> ActionResult:
        """
        Execute the use case to retweet a tweet.

        Args:
            tweet_id: The ID of the tweet to retweet

        Returns:
            ActionResult with success status

        Raises:
            TwitterRepositoryError: If the operation fails
        """
        logger.info(f"Retweeting tweet {tweet_id}")

        try:
            result = await self.twitter_repo.retweet(tweet_id)
            logger.info(f"Successfully retweeted tweet {tweet_id}")
            return result
        except TwitterRepositoryError as e:
            logger.error(f"Failed to retweet tweet {tweet_id}: {e.message}")
            raise


class PostTweetUseCase:
    """Use case for posting a new tweet."""

    def __init__(self, twitter_repo: ITwitterRepository):
        self.twitter_repo = twitter_repo

    async def execute(self, text: str) -> TweetPostResult:
        """
        Execute the use case to post a new tweet.

        Args:
            text: The tweet text

        Returns:
            TweetPostResult with success status and metadata

        Raises:
            TwitterRepositoryError: If the operation fails
        """
        logger.info("Posting new tweet")

        if not text or not text.strip():
            raise ValueError("Tweet text cannot be empty")
        if len(text) > 280:
            raise ValueError("Tweet text cannot exceed 280 characters")

        try:
            result = await self.twitter_repo.post_tweet(text)
            logger.info(f"Successfully posted tweet: {result.tweet_id}")
            return result
        except TwitterRepositoryError as e:
            logger.error(f"Failed to post tweet: {e.message}")
            raise
