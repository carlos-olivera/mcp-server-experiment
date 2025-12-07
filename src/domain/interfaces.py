"""Domain interfaces (ports) for dependency inversion."""

from abc import ABC, abstractmethod
from typing import List
from src.domain.models import Tweet, ActionResult, TweetPostResult, ReplyResult


class ITwitterRepository(ABC):
    """Interface for Twitter operations - to be implemented by infrastructure layer."""

    @abstractmethod
    async def read_last_tweets(self, username: str, count: int) -> List[Tweet]:
        """
        Read the last N tweets from a user's profile.

        Args:
            username: Twitter username (without @)
            count: Number of tweets to retrieve

        Returns:
            List of Tweet objects

        Raises:
            TwitterRepositoryError: If operation fails
        """
        pass

    @abstractmethod
    async def reply_to_tweet(self, tweet_id: str, text: str) -> ReplyResult:
        """
        Reply to a tweet.

        Args:
            tweet_id: The ID of the tweet to reply to
            text: The reply text

        Returns:
            ReplyResult with success status and metadata

        Raises:
            TwitterRepositoryError: If operation fails
        """
        pass

    @abstractmethod
    async def retweet(self, tweet_id: str) -> ActionResult:
        """
        Retweet (repost) a tweet.

        Args:
            tweet_id: The ID of the tweet to retweet

        Returns:
            ActionResult with success status

        Raises:
            TwitterRepositoryError: If operation fails
        """
        pass

    @abstractmethod
    async def post_tweet(self, text: str) -> TweetPostResult:
        """
        Post a new tweet.

        Args:
            text: The tweet text

        Returns:
            TweetPostResult with success status and tweet metadata

        Raises:
            TwitterRepositoryError: If operation fails
        """
        pass

    @abstractmethod
    async def read_last_mentions(self, count: int) -> List[Tweet]:
        """
        Read the last N mentions of the authenticated account.

        Args:
            count: Number of mentions to retrieve

        Returns:
            List of Tweet objects representing mentions

        Raises:
            TwitterRepositoryError: If operation fails
        """
        pass


class TwitterRepositoryError(Exception):
    """Base exception for Twitter repository operations."""

    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
