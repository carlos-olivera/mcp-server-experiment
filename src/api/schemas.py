"""Pydantic schemas for API request and response validation."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class ReadTweetsRequest(BaseModel):
    """Request schema for reading tweets."""

    username: str = Field(..., description="Twitter username (without @)", min_length=1)
    count: int = Field(5, description="Number of tweets to retrieve", ge=1, le=100)

    @validator('username')
    def username_no_at(cls, v):
        """Remove @ if present."""
        return v.lstrip('@')


class ReplyToTweetRequest(BaseModel):
    """Request schema for replying to a tweet."""

    tweet_id: str = Field(..., description="ID of the tweet to reply to", min_length=1)
    text: str = Field(..., description="Reply text", min_length=1, max_length=280)


class RetweetRequest(BaseModel):
    """Request schema for retweeting."""

    tweet_id: str = Field(..., description="ID of the tweet to retweet", min_length=1)


class PostTweetRequest(BaseModel):
    """Request schema for posting a tweet."""

    text: str = Field(..., description="Tweet text", min_length=1, max_length=280)


class TweetSchema(BaseModel):
    """Schema for a tweet."""

    id: str
    text: str
    author_username: str
    created_at: Optional[str] = None
    url: Optional[str] = None
    retweet_count: Optional[int] = None
    like_count: Optional[int] = None
    reply_count: Optional[int] = None


class ReadTweetsResponse(BaseModel):
    """Response schema for reading tweets."""

    success: bool
    tweets: List[TweetSchema]
    count: int


class ActionResponse(BaseModel):
    """Generic response schema for actions."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    error: str
    error_code: str
    detail: Optional[str] = None
