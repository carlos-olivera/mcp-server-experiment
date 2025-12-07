"""Extended use cases for mentions and MongoDB persistence."""

import logging
import re
from datetime import datetime
from typing import List
from src.domain.interfaces import ITwitterRepository, TwitterRepositoryError
from src.domain.models import (
    Tweet,
    StoredTweet,
    Mention,
    TweetType,
    IgnoredReason,
    Action,
    ReplyResult
)
from src.infrastructure.mongo_repository import MongoRepository

logger = logging.getLogger(__name__)


class GetUnansweredMentionsUseCase:
    """Use case for getting unanswered mentions with abuse prevention."""

    def __init__(
        self,
        twitter_repo: ITwitterRepository,
        mongo_repo: MongoRepository
    ):
        self.twitter_repo = twitter_repo
        self.mongo_repo = mongo_repo

    async def execute(self, count: int = 5, username: str = None) -> List[Mention]:
        """
        Get unanswered mentions with abuse prevention.

        Flow:
        1. Fetch last N*2 mentions from Twitter (buffer for filtering)
        2. Store/update each in MongoDB
        3. Get unanswered mentions from MongoDB (with abuse filtering)
        4. Return up to `count` mentions

        Args:
            count: Number of unanswered mentions to return
            username: Optional filter to get mentions only from this specific user

        Returns:
            List of Mention objects (with idTweet)

        Raises:
            TwitterRepositoryError: If Twitter scraping fails
        """
        if username:
            logger.info(f"Getting {count} unanswered mentions from @{username}")
        else:
            logger.info(f"Getting {count} unanswered mentions")

        # Step 1: Fetch mentions from Twitter (get more to account for filtering)
        buffer_count = count * 2
        try:
            raw_tweets = await self.twitter_repo.read_last_mentions(buffer_count)
            logger.info(f"Fetched {len(raw_tweets)} raw mentions from Twitter")
        except TwitterRepositoryError as e:
            logger.error(f"Failed to fetch mentions from Twitter: {e.message}")
            raise

        # Step 2: Store each mention in MongoDB
        for tweet in raw_tweets:
            # Parse mentioned users from tweet text
            mentioned_users = self._extract_mentioned_users(tweet.text)

            # Create Mention object
            mention = Mention(
                **StoredTweet.from_tweet(tweet, TweetType.MENTION).__dict__,
                mentioned_users=mentioned_users
            )

            # Store/update in MongoDB
            try:
                await self.mongo_repo.store_mention(mention)
            except Exception as e:
                logger.error(f"Failed to store mention {tweet.id}: {e}")
                # Continue with others even if one fails

        # Step 3: Get unanswered mentions with abuse filtering
        mentions = await self.mongo_repo.get_unanswered_mentions(
            limit=count,
            apply_abuse_filter=True,
            username=username
        )

        logger.info(f"Returning {len(mentions)} unanswered mentions")
        return mentions

    def _extract_mentioned_users(self, text: str) -> List[str]:
        """Extract @mentions from tweet text."""
        # Find all @username patterns
        mentions = re.findall(r'@(\w+)', text)
        return [f"@{m}" for m in mentions]


class GetUnansweredTweetsFromUserUseCase:
    """Use case for getting unanswered tweets from a specific user."""

    def __init__(
        self,
        twitter_repo: ITwitterRepository,
        mongo_repo: MongoRepository
    ):
        self.twitter_repo = twitter_repo
        self.mongo_repo = mongo_repo

    async def execute(self, username: str, count: int = 5) -> List[StoredTweet]:
        """
        Get unanswered tweets from a specific user.

        Flow:
        1. Fetch last N tweets from Twitter for this user
        2. Store/update each in MongoDB
        3. Get unanswered tweets from MongoDB
        4. Return up to `count` tweets

        Args:
            username: Twitter username (without @)
            count: Number of unanswered tweets to return

        Returns:
            List of StoredTweet objects

        Raises:
            TwitterRepositoryError: If Twitter scraping fails
        """
        logger.info(f"Getting {count} unanswered tweets from @{username}")

        # Step 1: Fetch tweets from Twitter
        try:
            raw_tweets = await self.twitter_repo.read_last_tweets(username, count * 2)
            logger.info(f"Fetched {len(raw_tweets)} tweets from @{username}")
        except TwitterRepositoryError as e:
            logger.error(f"Failed to fetch tweets from @{username}: {e.message}")
            raise

        # Step 2: Store each tweet in MongoDB
        for tweet in raw_tweets:
            stored_tweet = StoredTweet.from_tweet(tweet, TweetType.REGULAR)

            try:
                await self.mongo_repo.store_tweet(stored_tweet)
            except Exception as e:
                logger.error(f"Failed to store tweet {tweet.id}: {e}")

        # Step 3: Get unanswered tweets from MongoDB
        tweets = await self.mongo_repo.get_unanswered_tweets_from_user(
            username=username,
            limit=count
        )

        logger.info(f"Returning {len(tweets)} unanswered tweets from @{username}")
        return tweets


class ReplyByIdTweetUseCase:
    """Use case for replying to a tweet by its internal MongoDB ID."""

    def __init__(
        self,
        twitter_repo: ITwitterRepository,
        mongo_repo: MongoRepository
    ):
        self.twitter_repo = twitter_repo
        self.mongo_repo = mongo_repo

    async def execute(self, id_tweet: str, text: str, quoted: bool = False) -> ReplyResult:
        """
        Reply to a tweet using its internal MongoDB ID.

        Flow:
        1. Get tweet/mention from MongoDB by idTweet
        2. Reply to the tweet on Twitter using tweetId (or quote tweet if quoted=True)
        3. Mark as replied in MongoDB
        4. Log the action

        Args:
            id_tweet: Internal MongoDB UUID
            text: Reply text
            quoted: If True, post as quote tweet instead of reply

        Returns:
            ReplyResult with success status

        Raises:
            ValueError: If id_tweet not found
            TwitterRepositoryError: If reply fails
        """
        action_type = "quote_tweet" if quoted else "reply"
        logger.info(f"{'Quote tweeting' if quoted else 'Replying to'} idTweet={id_tweet}")

        # Step 1: Get the tweet/mention from MongoDB
        # Try mentions first, then tweets
        stored_item = await self.mongo_repo.get_mention_by_id_tweet(id_tweet)
        if not stored_item:
            stored_item = await self.mongo_repo.get_tweet_by_id_tweet(id_tweet)

        if not stored_item:
            error_msg = f"Tweet not found with idTweet={id_tweet}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if stored_item.replied_to:
            logger.warning(f"Tweet {id_tweet} already replied to")
            return ReplyResult(
                success=False,
                message=f"Tweet {id_tweet} has already been replied to",
                original_tweet_id=stored_item.tweet_id,
                error_code="ALREADY_REPLIED"
            )

        # Step 2: Reply or quote tweet on Twitter
        try:
            if quoted:
                result = await self.twitter_repo.quote_tweet(
                    stored_item.tweet_id,
                    text
                )
                logger.info(f"Successfully quote tweeted {stored_item.tweet_id}")
            else:
                result = await self.twitter_repo.reply_to_tweet(
                    stored_item.tweet_id,
                    text
                )
                logger.info(f"Successfully replied to tweet {stored_item.tweet_id}")
        except TwitterRepositoryError as e:
            logger.error(f"Failed to {action_type} tweet: {e.message}")

            # Log failed action
            action = Action(
                action_type=action_type,
                performed_at=datetime.utcnow(),
                success=False,
                target_tweet_id=stored_item.tweet_id,
                target_id_tweet=id_tweet,
                target_username=stored_item.author_username,
                error_message=e.message
            )
            await self.mongo_repo.log_action(action)

            raise

        # Step 3: Mark as replied in MongoDB
        # Assume reply tweet ID is in result data (would need to extract from actual reply)
        reply_tweet_id = result.reply_tweet_id or "unknown"

        if isinstance(stored_item, Mention):
            await self.mongo_repo.mark_mention_as_replied(id_tweet, reply_tweet_id)
        else:
            await self.mongo_repo.mark_tweet_as_replied(id_tweet, reply_tweet_id)

        # Step 4: Log successful action
        action = Action(
            action_type=action_type,
            performed_at=datetime.utcnow(),
            success=True,
            target_tweet_id=stored_item.tweet_id,
            target_id_tweet=id_tweet,
            target_username=stored_item.author_username,
            result_tweet_id=reply_tweet_id,
            metadata={
                "text": text,
                "quoted": quoted
            }
        )
        await self.mongo_repo.log_action(action)

        # Return result with internal IDs
        action_verb = "quote tweeted" if quoted else "replied to"
        return ReplyResult(
            success=True,
            message=f"Successfully {action_verb} tweet {id_tweet}",
            original_tweet_id=stored_item.tweet_id,
            reply_tweet_id=reply_tweet_id,
            data={"idTweet": id_tweet, "quoted": quoted}
        )
