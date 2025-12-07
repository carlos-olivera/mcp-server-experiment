"""Domain use cases - orchestrate business logic without framework dependencies."""

import logging
from typing import List, Optional
from datetime import datetime
from src.domain.interfaces import ITwitterRepository, TwitterRepositoryError
from src.domain.models import Tweet, ActionResult, TweetPostResult, ReplyResult, Action

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

    def __init__(self, twitter_repo: ITwitterRepository, mongo_repo=None):
        self.twitter_repo = twitter_repo
        self.mongo_repo = mongo_repo  # Optional MongoDB repository

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

            # If MongoDB is available, mark the tweet/mention as replied
            if self.mongo_repo:
                await self._mark_as_replied_in_mongodb(tweet_id, result.reply_tweet_id or "unknown", text)

            return result
        except TwitterRepositoryError as e:
            logger.error(f"Failed to reply to tweet {tweet_id}: {e.message}")

            # Log failed action if MongoDB is available
            if self.mongo_repo:
                await self._log_failed_reply(tweet_id, text, e.message)

            raise

    async def _mark_as_replied_in_mongodb(self, tweet_id: str, reply_tweet_id: str, reply_text: str):
        """Mark tweet/mention as replied in MongoDB if it exists."""
        try:
            # Try to find by tweetId in mentions collection
            mention = await self.mongo_repo.get_mention_by_twitter_id(tweet_id)
            if mention:
                await self.mongo_repo.mark_mention_as_replied(mention.id_tweet, reply_tweet_id)
                logger.info(f"Marked mention {tweet_id} as replied in MongoDB")

                # Log successful action
                action = Action(
                    action_type="reply",
                    performed_at=datetime.utcnow(),
                    success=True,
                    target_tweet_id=tweet_id,
                    target_id_tweet=mention.id_tweet,
                    target_username=mention.author_username,
                    result_tweet_id=reply_tweet_id,
                    metadata={"reply_text": reply_text}
                )
                await self.mongo_repo.log_action(action)
                return

            # Try to find in tweets collection
            tweet = await self.mongo_repo.get_tweet_by_twitter_id(tweet_id)
            if tweet:
                await self.mongo_repo.mark_tweet_as_replied(tweet.id_tweet, reply_tweet_id)
                logger.info(f"Marked tweet {tweet_id} as replied in MongoDB")

                # Log successful action
                action = Action(
                    action_type="reply",
                    performed_at=datetime.utcnow(),
                    success=True,
                    target_tweet_id=tweet_id,
                    target_id_tweet=tweet.id_tweet,
                    target_username=tweet.author_username,
                    result_tweet_id=reply_tweet_id,
                    metadata={"reply_text": reply_text}
                )
                await self.mongo_repo.log_action(action)
                return

            logger.info(f"Tweet {tweet_id} not found in MongoDB, skipping mark as replied")

        except Exception as e:
            logger.error(f"Failed to mark tweet {tweet_id} as replied in MongoDB: {e}")
            # Don't raise - MongoDB marking is optional

    async def _log_failed_reply(self, tweet_id: str, reply_text: str, error_message: str):
        """Log failed reply action to MongoDB."""
        try:
            # Try to get tweet info for logging
            mention = await self.mongo_repo.get_mention_by_twitter_id(tweet_id)
            if not mention:
                tweet = await self.mongo_repo.get_tweet_by_twitter_id(tweet_id)
                if tweet:
                    mention = tweet

            action = Action(
                action_type="reply",
                performed_at=datetime.utcnow(),
                success=False,
                target_tweet_id=tweet_id,
                target_id_tweet=mention.id_tweet if mention else None,
                target_username=mention.author_username if mention else "unknown",
                error_message=error_message,
                metadata={"reply_text": reply_text}
            )
            await self.mongo_repo.log_action(action)
        except Exception as e:
            logger.error(f"Failed to log action to MongoDB: {e}")


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
