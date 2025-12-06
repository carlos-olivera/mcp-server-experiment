"""REST API routes for Twitter operations."""

import logging
from fastapi import APIRouter, HTTPException, status
from src.api.schemas import (
    ReadTweetsRequest,
    ReadTweetsResponse,
    ReplyToTweetRequest,
    RetweetRequest,
    PostTweetRequest,
    ActionResponse,
    ErrorResponse,
    TweetSchema
)
from src.domain.use_cases import (
    ReadLastTweetsUseCase,
    ReplyToTweetUseCase,
    RetweetUseCase,
    PostTweetUseCase
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


def configure_dependencies(
    read_tweets: ReadLastTweetsUseCase,
    reply: ReplyToTweetUseCase,
    retweet: RetweetUseCase,
    post_tweet: PostTweetUseCase
):
    """Configure use case dependencies for routes."""
    global _read_tweets_use_case, _reply_use_case, _retweet_use_case, _post_tweet_use_case
    _read_tweets_use_case = read_tweets
    _reply_use_case = reply
    _retweet_use_case = retweet
    _post_tweet_use_case = post_tweet


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
