"""Domain models representing Twitter entities and responses."""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid


@dataclass
class Tweet:
    """Represents a tweet with its metadata."""

    id: str
    text: str
    author_username: str
    created_at: Optional[datetime] = None
    url: Optional[str] = None
    retweet_count: Optional[int] = None
    like_count: Optional[int] = None
    reply_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        data = asdict(self)
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        return data


@dataclass
class ActionResult:
    """Represents the result of a Twitter action."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class TweetPostResult(ActionResult):
    """Result of posting a tweet."""

    tweet_id: Optional[str] = None
    tweet_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        base = super().to_dict()
        base.update({
            "tweet_id": self.tweet_id,
            "tweet_url": self.tweet_url
        })
        return base


@dataclass
class ReplyResult(ActionResult):
    """Result of replying to a tweet."""

    original_tweet_id: Optional[str] = None
    reply_tweet_id: Optional[str] = None
    reply_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        base = super().to_dict()
        base.update({
            "original_tweet_id": self.original_tweet_id,
            "reply_tweet_id": self.reply_tweet_id,
            "reply_url": self.reply_url
        })
        return base


# New models for MongoDB persistence and mentions

class TweetType(str, Enum):
    """Types of tweets we track."""
    MENTION = "mention"
    REGULAR = "regular"
    REPLY = "reply"
    POSTED_BY_US = "posted_by_us"


class IgnoredReason(str, Enum):
    """Reasons a tweet/mention was ignored."""
    SPAM = "spam"
    DUPLICATE_USER = "duplicate_user"
    BLOCKED_USER = "blocked_user"
    MANUAL = "manual"


class BlockedReason(str, Enum):
    """Reasons a user was blocked."""
    EXCESSIVE_MENTIONS = "excessive_mentions"
    SPAM = "spam"
    MANUAL = "manual"


@dataclass
class StoredTweet:
    """Tweet as stored in MongoDB with tracking metadata."""

    id_tweet: str  # MongoDB-assigned UUID
    tweet_id: str  # Twitter's tweet ID
    text: str
    author_username: str
    created_at: datetime
    url: str
    tweet_type: TweetType

    # Engagement metrics
    retweet_count: Optional[int] = None
    like_count: Optional[int] = None
    reply_count: Optional[int] = None

    # Our interaction tracking
    replied_to: bool = False
    replied_at: Optional[datetime] = None
    reply_tweet_id: Optional[str] = None

    reposted_by_us: bool = False
    reposted_at: Optional[datetime] = None

    ignored: bool = False
    ignored_reason: Optional[IgnoredReason] = None
    ignored_at: Optional[datetime] = None

    # Metadata
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_tweet(cls, tweet: Tweet, tweet_type: TweetType = TweetType.REGULAR) -> 'StoredTweet':
        """Create StoredTweet from Tweet domain model."""
        return cls(
            id_tweet=str(uuid.uuid4()),
            tweet_id=tweet.id,
            text=tweet.text,
            author_username=tweet.author_username,
            created_at=tweet.created_at or datetime.utcnow(),
            url=tweet.url or "",
            tweet_type=tweet_type,
            retweet_count=tweet.retweet_count,
            like_count=tweet.like_count,
            reply_count=tweet.reply_count
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = {
            "idTweet": self.id_tweet,
            "tweetId": self.tweet_id,
            "text": self.text,
            "authorUsername": self.author_username,
            "createdAt": self.created_at,
            "url": self.url,
            "type": self.tweet_type.value,
            "retweetCount": self.retweet_count,
            "likeCount": self.like_count,
            "replyCount": self.reply_count,
            "repliedTo": self.replied_to,
            "repliedAt": self.replied_at,
            "replyTweetId": self.reply_tweet_id,
            "repostedByUs": self.reposted_by_us,
            "repostedAt": self.reposted_at,
            "ignored": self.ignored,
            "ignoredReason": self.ignored_reason.value if self.ignored_reason else None,
            "ignoredAt": self.ignored_at,
            "firstSeenAt": self.first_seen_at,
            "lastUpdatedAt": self.last_updated_at
        }
        return {k: v for k, v in data.items() if v is not None}

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "idTweet": self.id_tweet,
            "tweetId": self.tweet_id,
            "text": self.text,
            "authorUsername": self.author_username,
            "createdAt": self.created_at.isoformat(),
            "url": self.url,
            "type": self.tweet_type.value,
            "repliedTo": self.replied_to,
            "ignored": self.ignored
        }


@dataclass
class Mention(StoredTweet):
    """Mention-specific extension of StoredTweet."""

    mentioned_users: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        data = super().to_dict()
        data["mentionedUsers"] = self.mentioned_users
        return data

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        data = super().to_api_dict()
        data["mentionedUsers"] = self.mentioned_users
        return data


@dataclass
class BlockedUser:
    """User that has been blocked due to abuse."""

    username: str
    blocked_at: datetime
    blocked_reason: BlockedReason

    user_id: Optional[str] = None
    total_mentions: int = 0
    ignored_mentions: int = 0
    first_seen_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "username": self.username,
            "userId": self.user_id,
            "blockedAt": self.blocked_at,
            "blockedReason": self.blocked_reason.value,
            "totalMentions": self.total_mentions,
            "ignoredMentions": self.ignored_mentions,
            "firstSeenAt": self.first_seen_at,
            "lastActivityAt": self.last_activity_at
        }


@dataclass
class Action:
    """Audit log of actions we've taken."""

    action_type: str  # "reply" | "repost" | "post" | "ignore" | "block"
    performed_at: datetime
    success: bool

    target_tweet_id: Optional[str] = None
    target_id_tweet: Optional[str] = None
    target_username: Optional[str] = None
    result_tweet_id: Optional[str] = None
    reason: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "actionType": self.action_type,
            "targetTweetId": self.target_tweet_id,
            "targetIdTweet": self.target_id_tweet,
            "targetUsername": self.target_username,
            "resultTweetId": self.result_tweet_id,
            "reason": self.reason,
            "success": self.success,
            "errorMessage": self.error_message,
            "performedAt": self.performed_at,
            "metadata": self.metadata
        }
