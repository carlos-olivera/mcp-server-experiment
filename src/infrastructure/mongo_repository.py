"""MongoDB repository for persisting tweets, mentions, and user data."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError
from src.config import config
from src.domain.models import (
    StoredTweet,
    Mention,
    BlockedUser,
    Action,
    TweetType,
    IgnoredReason,
    BlockedReason,
    Tweet
)

logger = logging.getLogger(__name__)


class MongoRepository:
    """Repository for MongoDB persistence of tweets, mentions, and user data."""

    def __init__(self, client: Optional[AsyncIOMotorClient] = None):
        """
        Initialize MongoDB repository.

        Args:
            client: Optional AsyncIOMotorClient. If None, creates one from config.
        """
        if client:
            self.client = client
        else:
            self.client = AsyncIOMotorClient(config.get_mongo_uri())

        self.db: AsyncIOMotorDatabase = self.client[config.MONGO_DB]

        # Collections
        self.tweets: AsyncIOMotorCollection = self.db.tweets
        self.mentions: AsyncIOMotorCollection = self.db.mentions
        self.blocked_users: AsyncIOMotorCollection = self.db.blocked_users
        self.actions: AsyncIOMotorCollection = self.db.actions

    async def initialize(self) -> None:
        """Create indexes for optimal query performance."""
        logger.info("Initializing MongoDB indexes")

        try:
            # Tweets collection indexes
            await self.tweets.create_index("tweetId", unique=True)
            await self.tweets.create_index("idTweet", unique=True)
            await self.tweets.create_index([("type", 1), ("repliedTo", 1), ("ignored", 1)])
            await self.tweets.create_index([("authorUsername", 1), ("createdAt", -1)])
            await self.tweets.create_index([("ignored", 1), ("firstSeenAt", -1)])

            # Mentions collection indexes
            await self.mentions.create_index("tweetId", unique=True)
            await self.mentions.create_index("idTweet", unique=True)
            await self.mentions.create_index([("repliedTo", 1), ("ignored", 1), ("firstSeenAt", -1)])
            await self.mentions.create_index([("authorUsername", 1), ("ignored", 1)])

            # Blocked users collection indexes
            await self.blocked_users.create_index("username", unique=True)
            await self.blocked_users.create_index([("blockedAt", -1)])

            # Actions collection indexes
            await self.actions.create_index([("actionType", 1), ("performedAt", -1)])
            await self.actions.create_index("targetTweetId")

            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating MongoDB indexes: {e}")
            raise

    async def close(self) -> None:
        """Close MongoDB connection."""
        logger.info("Closing MongoDB connection")
        self.client.close()

    # Tweet operations

    async def store_tweet(self, tweet: StoredTweet) -> StoredTweet:
        """
        Store or update a tweet in MongoDB.

        Args:
            tweet: StoredTweet to store

        Returns:
            The stored tweet (with updated timestamp)

        Raises:
            Exception if storage fails
        """
        tweet.last_updated_at = datetime.utcnow()

        try:
            # Try to insert (will fail if tweet_id already exists)
            await self.tweets.insert_one(tweet.to_dict())
            logger.debug(f"Stored new tweet: {tweet.id_tweet} ({tweet.tweet_id})")
            return tweet

        except DuplicateKeyError:
            # Tweet already exists, update it
            result = await self.tweets.update_one(
                {"tweetId": tweet.tweet_id},
                {"$set": tweet.to_dict()}
            )
            logger.debug(f"Updated existing tweet: {tweet.tweet_id}")
            return tweet

        except Exception as e:
            logger.error(f"Error storing tweet {tweet.tweet_id}: {e}")
            raise

    async def get_tweet_by_id_tweet(self, id_tweet: str) -> Optional[StoredTweet]:
        """
        Retrieve tweet by internal MongoDB ID.

        Args:
            id_tweet: Internal MongoDB UUID

        Returns:
            StoredTweet if found, None otherwise
        """
        doc = await self.tweets.find_one({"idTweet": id_tweet})
        if not doc:
            return None

        return self._doc_to_stored_tweet(doc)

    async def get_tweet_by_twitter_id(self, tweet_id: str) -> Optional[StoredTweet]:
        """
        Retrieve tweet by Twitter's tweet ID.

        Args:
            tweet_id: Twitter's tweet ID

        Returns:
            StoredTweet if found, None otherwise
        """
        doc = await self.tweets.find_one({"tweetId": tweet_id})
        if not doc:
            return None

        return self._doc_to_stored_tweet(doc)

    async def get_unanswered_tweets_from_user(
        self,
        username: str,
        limit: int = 5
    ) -> List[StoredTweet]:
        """
        Get unanswered tweets from a specific user.

        Args:
            username: Twitter username
            limit: Maximum number of tweets to return

        Returns:
            List of StoredTweet objects that haven't been replied to
        """
        cursor = self.tweets.find({
            "authorUsername": username,
            "type": TweetType.REGULAR.value,
            "repliedTo": False,
            "ignored": False
        }).sort("createdAt", -1).limit(limit)

        tweets = []
        async for doc in cursor:
            tweets.append(self._doc_to_stored_tweet(doc))

        logger.info(f"Retrieved {len(tweets)} unanswered tweets from @{username}")
        return tweets

    async def mark_tweet_as_replied(
        self,
        id_tweet: str,
        reply_tweet_id: str
    ) -> bool:
        """
        Mark a tweet as replied to.

        Args:
            id_tweet: Internal MongoDB UUID
            reply_tweet_id: Twitter ID of the reply tweet

        Returns:
            True if updated successfully
        """
        result = await self.tweets.update_one(
            {"idTweet": id_tweet},
            {
                "$set": {
                    "repliedTo": True,
                    "repliedAt": datetime.utcnow(),
                    "replyTweetId": reply_tweet_id,
                    "lastUpdatedAt": datetime.utcnow()
                }
            }
        )

        success = result.modified_count > 0
        if success:
            logger.info(f"Marked tweet {id_tweet} as replied with {reply_tweet_id}")
        else:
            logger.warning(f"Tweet {id_tweet} not found or already marked as replied")

        return success

    async def mark_tweet_as_ignored(
        self,
        id_tweet: str,
        reason: IgnoredReason
    ) -> bool:
        """
        Mark a tweet as ignored.

        Args:
            id_tweet: Internal MongoDB UUID
            reason: Reason for ignoring

        Returns:
            True if updated successfully
        """
        result = await self.tweets.update_one(
            {"idTweet": id_tweet},
            {
                "$set": {
                    "ignored": True,
                    "ignoredReason": reason.value,
                    "ignoredAt": datetime.utcnow(),
                    "lastUpdatedAt": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    # Mention operations

    async def store_mention(self, mention: Mention) -> Mention:
        """
        Store or update a mention in MongoDB.

        Args:
            mention: Mention to store

        Returns:
            The stored mention

        Raises:
            Exception if storage fails
        """
        mention.last_updated_at = datetime.utcnow()

        try:
            await self.mentions.insert_one(mention.to_dict())
            logger.debug(f"Stored new mention: {mention.id_tweet} from @{mention.author_username}")
            return mention

        except DuplicateKeyError:
            result = await self.mentions.update_one(
                {"tweetId": mention.tweet_id},
                {"$set": mention.to_dict()}
            )
            logger.debug(f"Updated existing mention: {mention.tweet_id}")
            return mention

        except Exception as e:
            logger.error(f"Error storing mention {mention.tweet_id}: {e}")
            raise

    async def get_mention_by_id_tweet(self, id_tweet: str) -> Optional[Mention]:
        """
        Retrieve mention by internal MongoDB ID.

        Args:
            id_tweet: Internal MongoDB UUID

        Returns:
            Mention if found, None otherwise
        """
        doc = await self.mentions.find_one({"idTweet": id_tweet})
        if not doc:
            return None

        return self._doc_to_mention(doc)

    async def get_unanswered_mentions(
        self,
        limit: int = 5,
        apply_abuse_filter: bool = True
    ) -> List[Mention]:
        """
        Get unanswered mentions with abuse prevention.

        Args:
            limit: Maximum number of mentions to return
            apply_abuse_filter: Whether to apply duplicate user filtering

        Returns:
            List of Mention objects
        """
        # Get blocked users
        blocked_usernames = await self.get_blocked_usernames()

        # Query for unanswered, non-ignored mentions from non-blocked users
        # Get more than needed to allow for filtering
        buffer_limit = limit * 3  # Get 3x to have room for filtering

        cursor = self.mentions.find({
            "repliedTo": False,
            "ignored": False,
            "authorUsername": {"$nin": blocked_usernames}
        }).sort("firstSeenAt", -1).limit(buffer_limit)

        all_mentions = []
        async for doc in cursor:
            all_mentions.append(self._doc_to_mention(doc))

        if not apply_abuse_filter:
            return all_mentions[:limit]

        # Apply abuse prevention: max 1 mention per user in result set
        filtered_mentions = []
        seen_users = set()
        mentions_to_ignore = []

        for mention in all_mentions:
            if len(filtered_mentions) >= limit:
                break

            username = mention.author_username

            if username not in seen_users:
                # First mention from this user - include it
                filtered_mentions.append(mention)
                seen_users.add(username)
            else:
                # Duplicate from same user - mark for ignoring
                mentions_to_ignore.append((mention.id_tweet, username))

        # Mark duplicates as ignored
        for id_tweet, username in mentions_to_ignore:
            await self.mark_mention_as_ignored(id_tweet, IgnoredReason.DUPLICATE_USER)
            logger.info(f"Ignored duplicate mention {id_tweet} from @{username}")

            # Check if user should be blocked
            await self.check_and_block_user(username)

        logger.info(
            f"Retrieved {len(filtered_mentions)} unanswered mentions "
            f"(filtered {len(mentions_to_ignore)} duplicates)"
        )

        return filtered_mentions

    async def mark_mention_as_replied(
        self,
        id_tweet: str,
        reply_tweet_id: str
    ) -> bool:
        """
        Mark a mention as replied to.

        Args:
            id_tweet: Internal MongoDB UUID
            reply_tweet_id: Twitter ID of the reply tweet

        Returns:
            True if updated successfully
        """
        result = await self.mentions.update_one(
            {"idTweet": id_tweet},
            {
                "$set": {
                    "repliedTo": True,
                    "repliedAt": datetime.utcnow(),
                    "replyTweetId": reply_tweet_id,
                    "lastUpdatedAt": datetime.utcnow()
                }
            }
        )

        success = result.modified_count > 0
        if success:
            logger.info(f"Marked mention {id_tweet} as replied")

        return success

    async def mark_mention_as_ignored(
        self,
        id_tweet: str,
        reason: IgnoredReason
    ) -> bool:
        """
        Mark a mention as ignored.

        Args:
            id_tweet: Internal MongoDB UUID
            reason: Reason for ignoring

        Returns:
            True if updated successfully
        """
        result = await self.mentions.update_one(
            {"idTweet": id_tweet},
            {
                "$set": {
                    "ignored": True,
                    "ignoredReason": reason.value,
                    "ignoredAt": datetime.utcnow(),
                    "lastUpdatedAt": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    # Blocked user operations

    async def is_user_blocked(self, username: str) -> bool:
        """Check if a user is blocked."""
        doc = await self.blocked_users.find_one({"username": username})
        return doc is not None

    async def get_blocked_usernames(self) -> List[str]:
        """Get list of all blocked usernames."""
        cursor = self.blocked_users.find({}, {"username": 1})
        usernames = []
        async for doc in cursor:
            usernames.append(doc["username"])
        return usernames

    async def block_user(self, blocked_user: BlockedUser) -> bool:
        """
        Block a user.

        Args:
            blocked_user: BlockedUser object

        Returns:
            True if blocked successfully (not already blocked)
        """
        try:
            await self.blocked_users.insert_one(blocked_user.to_dict())
            logger.warning(
                f"Blocked user @{blocked_user.username} - "
                f"reason: {blocked_user.blocked_reason.value}"
            )
            return True

        except DuplicateKeyError:
            logger.debug(f"User @{blocked_user.username} already blocked")
            return False

        except Exception as e:
            logger.error(f"Error blocking user @{blocked_user.username}: {e}")
            raise

    async def check_and_block_user(self, username: str) -> Optional[BlockedUser]:
        """
        Check if user should be blocked based on ignored mention count.

        Args:
            username: Twitter username

        Returns:
            BlockedUser if user was blocked, None otherwise
        """
        # Count ignored mentions from this user
        ignored_count = await self.mentions.count_documents({
            "authorUsername": username,
            "ignored": True
        })

        if ignored_count >= config.MAX_IGNORED_BEFORE_BLOCK:
            # Block the user
            blocked_user = BlockedUser(
                username=username,
                blocked_at=datetime.utcnow(),
                blocked_reason=BlockedReason.EXCESSIVE_MENTIONS,
                ignored_mentions=ignored_count
            )

            success = await self.block_user(blocked_user)
            if success:
                return blocked_user

        return None

    # Action logging

    async def log_action(self, action: Action) -> None:
        """
        Log an action to the audit trail.

        Args:
            action: Action to log
        """
        try:
            await self.actions.insert_one(action.to_dict())
            logger.debug(f"Logged action: {action.action_type} - success={action.success}")

        except Exception as e:
            logger.error(f"Error logging action: {e}")
            # Don't raise - logging failure shouldn't break the operation

    # Helper methods

    def _doc_to_stored_tweet(self, doc: Dict[str, Any]) -> StoredTweet:
        """Convert MongoDB document to StoredTweet."""
        return StoredTweet(
            id_tweet=doc["idTweet"],
            tweet_id=doc["tweetId"],
            text=doc["text"],
            author_username=doc["authorUsername"],
            created_at=doc["createdAt"],
            url=doc["url"],
            tweet_type=TweetType(doc["type"]),
            retweet_count=doc.get("retweetCount"),
            like_count=doc.get("likeCount"),
            reply_count=doc.get("replyCount"),
            replied_to=doc.get("repliedTo", False),
            replied_at=doc.get("repliedAt"),
            reply_tweet_id=doc.get("replyTweetId"),
            reposted_by_us=doc.get("repostedByUs", False),
            reposted_at=doc.get("repostedAt"),
            ignored=doc.get("ignored", False),
            ignored_reason=IgnoredReason(doc["ignoredReason"]) if doc.get("ignoredReason") else None,
            ignored_at=doc.get("ignoredAt"),
            first_seen_at=doc.get("firstSeenAt", datetime.utcnow()),
            last_updated_at=doc.get("lastUpdatedAt", datetime.utcnow())
        )

    def _doc_to_mention(self, doc: Dict[str, Any]) -> Mention:
        """Convert MongoDB document to Mention."""
        stored_tweet = self._doc_to_stored_tweet(doc)
        return Mention(
            **stored_tweet.__dict__,
            mentioned_users=doc.get("mentionedUsers", [])
        )
