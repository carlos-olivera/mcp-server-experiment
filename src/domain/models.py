"""Domain models representing Twitter entities and responses."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any


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
