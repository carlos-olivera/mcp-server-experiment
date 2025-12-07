"""REST API routes for Twitter operations."""

import logging
from fastapi import APIRouter, HTTPException, status, Query
from src.api.schemas import (
    ReadTweetsRequest,
    ReadTweetsResponse,
    ReplyToTweetRequest,
    RetweetRequest,
    PostTweetRequest,
    ActionResponse,
    ErrorResponse,
    TweetSchema,
    UnansweredMentionsResponse,
    UnansweredTweetsResponse,
    ReplyByIdRequest
)
from src.domain.use_cases import (
    ReadLastTweetsUseCase,
    ReplyToTweetUseCase,
    RetweetUseCase,
    PostTweetUseCase
)
from src.domain.use_cases_extended import (
    GetUnansweredMentionsUseCase,
    GetUnansweredTweetsFromUserUseCase,
    ReplyByIdTweetUseCase
)
from src.domain.interfaces import TwitterRepositoryError

logger = logging.getLogger(__name__)

# Router will be configured with dependencies in app.py
router = APIRouter(prefix="/api/v1", tags=["twitter"])


# Dependencies will be injected by app.py
_read_tweets_use_case: ReadLastTweetsUseCase = None
_reply_use_case: ReplyToTweetUseCase = None
_retweet_use_case: RetweetUseCase = None
_post_tweet_use_case: PostTweetUseCase = None

# New MongoDB-backed use cases
_get_unanswered_mentions_use_case: GetUnansweredMentionsUseCase = None
_get_unanswered_tweets_from_user_use_case: GetUnansweredTweetsFromUserUseCase = None
_reply_by_id_use_case: ReplyByIdTweetUseCase = None


def configure_dependencies(
    read_tweets: ReadLastTweetsUseCase,
    reply: ReplyToTweetUseCase,
    retweet: RetweetUseCase,
    post_tweet: PostTweetUseCase,
    get_unanswered_mentions: GetUnansweredMentionsUseCase = None,
    get_unanswered_tweets_from_user: GetUnansweredTweetsFromUserUseCase = None,
    reply_by_id: ReplyByIdTweetUseCase = None
):
    """Configure use case dependencies for routes."""
    global _read_tweets_use_case, _reply_use_case, _retweet_use_case, _post_tweet_use_case
    global _get_unanswered_mentions_use_case, _get_unanswered_tweets_from_user_use_case, _reply_by_id_use_case

    _read_tweets_use_case = read_tweets
    _reply_use_case = reply
    _retweet_use_case = retweet
    _post_tweet_use_case = post_tweet

    # MongoDB-backed use cases
    _get_unanswered_mentions_use_case = get_unanswered_mentions
    _get_unanswered_tweets_from_user_use_case = get_unanswered_tweets_from_user
    _reply_by_id_use_case = reply_by_id


@router.post("/read_tweets", response_model=ReadTweetsResponse)
async def read_tweets(request: ReadTweetsRequest):
    """
    Read the last N tweets from a user's profile.

    Args:
        request: ReadTweetsRequest with username and count

    Returns:
        ReadTweetsResponse with list of tweets

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"API request: read_tweets for @{request.username}, count={request.count}")

    try:
        tweets = await _read_tweets_use_case.execute(request.username, request.count)

        # Convert domain models to API schemas
        tweet_schemas = [TweetSchema(**tweet.to_dict()) for tweet in tweets]

        return ReadTweetsResponse(
            success=True,
            tweets=tweet_schemas,
            count=len(tweet_schemas)
        )

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error reading tweets: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": e.message,
                "error_code": e.error_code
            }
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR"
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error reading tweets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )


@router.post("/reply", response_model=ActionResponse)
async def reply_to_tweet(request: ReplyToTweetRequest):
    """
    Reply to a tweet.

    Args:
        request: ReplyToTweetRequest with tweet_id and text

    Returns:
        ActionResponse with success status

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"API request: reply to tweet {request.tweet_id}")

    try:
        result = await _reply_use_case.execute(request.tweet_id, request.text)

        return ActionResponse(
            success=result.success,
            message=result.message,
            data=result.to_dict()
        )

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error replying to tweet: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": e.message,
                "error_code": e.error_code
            }
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR"
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error replying to tweet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )


@router.post("/retweet", response_model=ActionResponse)
async def retweet(request: RetweetRequest):
    """
    Retweet (repost) a tweet.

    Args:
        request: RetweetRequest with tweet_id

    Returns:
        ActionResponse with success status

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"API request: retweet {request.tweet_id}")

    try:
        result = await _retweet_use_case.execute(request.tweet_id)

        return ActionResponse(
            success=result.success,
            message=result.message,
            data=result.to_dict()
        )

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error retweeting: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": e.message,
                "error_code": e.error_code
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error retweeting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )


@router.post("/post_tweet", response_model=ActionResponse)
async def post_tweet(request: PostTweetRequest):
    """
    Post a new tweet.

    Args:
        request: PostTweetRequest with text

    Returns:
        ActionResponse with success status and tweet metadata

    Raises:
        HTTPException: If operation fails
    """
    logger.info("API request: post new tweet")

    try:
        result = await _post_tweet_use_case.execute(request.text)

        return ActionResponse(
            success=result.success,
            message=result.message,
            data=result.to_dict()
        )

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error posting tweet: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": e.message,
                "error_code": e.error_code
            }
        )
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR"
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error posting tweet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "twitter-mcp-agent"}


# New MongoDB-backed endpoints

@router.get("/mentions/unanswered", response_model=UnansweredMentionsResponse)
async def get_unanswered_mentions(
    count: int = Query(5, ge=1, le=50),
    username: str = Query(None, description="Optional: filter mentions from specific user")
):
    """
    Get unanswered mentions with abuse prevention.

    This endpoint:
    - Fetches recent mentions from Twitter
    - Stores them in MongoDB
    - Returns unanswered mentions (max 1 per user per batch, unless filtering by username)
    - Auto-blocks users with 10+ ignored mentions

    Args:
        count: Number of unanswered mentions to return (1-50)
        username: Optional filter to get mentions only from this specific user

    Returns:
        UnansweredMentionsResponse with list of mentions

    Raises:
        HTTPException: If operation fails
    """
    if username:
        username = username.lstrip('@')
        logger.info(f"API request: get {count} unanswered mentions from @{username}")
    else:
        logger.info(f"API request: get {count} unanswered mentions")

    try:
        mentions = await _get_unanswered_mentions_use_case.execute(count, username)

        # Convert to API format
        mentions_data = [m.to_api_dict() for m in mentions]

        return UnansweredMentionsResponse(
            success=True,
            mentions=mentions_data,
            count=len(mentions_data),
            username=username
        )

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error fetching mentions: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": e.message,
                "error_code": e.error_code
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error fetching mentions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )


@router.get("/tweets/unanswered/{username}", response_model=UnansweredTweetsResponse)
async def get_unanswered_tweets_from_user(username: str, count: int = Query(5, ge=1, le=50)):
    """
    Get unanswered tweets from a specific user.

    This endpoint:
    - Fetches recent tweets from the user
    - Stores them in MongoDB
    - Returns only unanswered tweets

    Args:
        username: Twitter username (without @)
        count: Number of unanswered tweets to return (1-50)

    Returns:
        UnansweredTweetsResponse with list of tweets

    Raises:
        HTTPException: If operation fails
    """
    username = username.lstrip('@')
    logger.info(f"API request: get {count} unanswered tweets from @{username}")

    try:
        tweets = await _get_unanswered_tweets_from_user_use_case.execute(username, count)

        # Convert to API format
        tweets_data = [t.to_api_dict() for t in tweets]

        return UnansweredTweetsResponse(
            success=True,
            tweets=tweets_data,
            count=len(tweets_data),
            username=username
        )

    except TwitterRepositoryError as e:
        logger.error(f"Twitter error fetching tweets from @{username}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": e.message,
                "error_code": e.error_code
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error fetching tweets from @{username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )


@router.post("/reply_by_id", response_model=ActionResponse)
async def reply_by_id_tweet(request: ReplyByIdRequest):
    """
    Reply to a tweet using its internal MongoDB ID.

    This endpoint:
    - Looks up the tweet/mention by idTweet in MongoDB
    - Posts a reply or quote tweet on Twitter (based on quoted parameter)
    - Marks the tweet as replied in MongoDB
    - Logs the action

    Args:
        request: ReplyByIdRequest with idTweet, text, and optional quoted flag

    Returns:
        ActionResponse with success status

    Raises:
        HTTPException: If operation fails or tweet not found
    """
    action_type = "quote tweet" if request.quoted else "reply"
    logger.info(f"API request: {action_type} to idTweet={request.idTweet}")

    try:
        result = await _reply_by_id_use_case.execute(
            request.idTweet,
            request.text,
            quoted=request.quoted
        )

        return ActionResponse(
            success=result.success,
            message=result.message,
            data=result.to_dict()
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": str(e),
                "error_code": "NOT_FOUND"
            }
        )
    except TwitterRepositoryError as e:
        logger.error(f"Twitter error replying: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": e.message,
                "error_code": e.error_code
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error replying: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )
