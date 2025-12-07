"""FastAPI application setup and lifecycle management."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from src.api import routes
from src.config import config
from src.infrastructure.logging_config import setup_logging
from src.infrastructure.browser_manager import BrowserManager
from src.infrastructure.twitter_repository import PlaywrightTwitterRepository
from src.infrastructure.mongo_repository import MongoRepository
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

logger = logging.getLogger(__name__)

# Global instances
browser_manager: BrowserManager = None
twitter_repo: PlaywrightTwitterRepository = None
mongo_repo: MongoRepository = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of browser, MongoDB, and other resources.
    """
    global browser_manager, twitter_repo, mongo_repo

    # Startup
    logger.info("Starting Twitter MCP Agent REST API")

    try:
        # Initialize MongoDB
        logger.info("Initializing MongoDB connection")
        mongo_repo = MongoRepository()
        await mongo_repo.initialize()
        logger.info(f"MongoDB connected to {config.MONGO_HOST}:{config.MONGO_PORT}/{config.MONGO_DB}")

        # Initialize browser manager
        browser_manager = BrowserManager()
        await browser_manager.start()
        logger.info("Browser manager started")

        # Initialize Twitter repository
        twitter_repo = PlaywrightTwitterRepository(browser_manager)
        logger.info("Twitter repository initialized")

        # Initialize original use cases (now with optional MongoDB support)
        read_tweets_uc = ReadLastTweetsUseCase(twitter_repo)
        reply_uc = ReplyToTweetUseCase(twitter_repo, mongo_repo)  # Now with MongoDB
        retweet_uc = RetweetUseCase(twitter_repo)
        post_tweet_uc = PostTweetUseCase(twitter_repo)

        # Initialize MongoDB-backed use cases
        get_unanswered_mentions_uc = GetUnansweredMentionsUseCase(twitter_repo, mongo_repo)
        get_unanswered_tweets_uc = GetUnansweredTweetsFromUserUseCase(twitter_repo, mongo_repo)
        reply_by_id_uc = ReplyByIdTweetUseCase(twitter_repo, mongo_repo)

        # Configure route dependencies
        routes.configure_dependencies(
            read_tweets=read_tweets_uc,
            reply=reply_uc,
            retweet=retweet_uc,
            post_tweet=post_tweet_uc,
            get_unanswered_mentions=get_unanswered_mentions_uc,
            get_unanswered_tweets_from_user=get_unanswered_tweets_uc,
            reply_by_id=reply_by_id_uc
        )
        logger.info("Use cases configured")

        logger.info("REST API startup complete")

        yield

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

    finally:
        # Shutdown
        logger.info("Shutting down Twitter MCP Agent REST API")

        if mongo_repo:
            await mongo_repo.close()
            logger.info("MongoDB connection closed")

        if browser_manager:
            await browser_manager.stop()
            logger.info("Browser manager stopped")

        logger.info("REST API shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    # Setup logging
    setup_logging()

    # Create FastAPI app
    app = FastAPI(
        title="Twitter MCP Agent API",
        description="REST API for Twitter automation via MCP",
        version="1.0.0",
        lifespan=lifespan
    )

    # Include routers
    app.include_router(routes.router)

    # Add exception handler for uncaught exceptions
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR"
            }
        )

    logger.info(f"FastAPI app created: {app.title}")

    return app


# Create app instance
app = create_app()
