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
from src.domain.use_cases import (
    ReadLastTweetsUseCase,
    ReplyToTweetUseCase,
    RetweetUseCase,
    PostTweetUseCase
)

logger = logging.getLogger(__name__)

# Global instances
browser_manager: BrowserManager = None
twitter_repo: PlaywrightTwitterRepository = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of browser and other resources.
    """
    global browser_manager, twitter_repo

    # Startup
    logger.info("Starting Twitter MCP Agent REST API")

    try:
        # Initialize browser manager
        browser_manager = BrowserManager()
        await browser_manager.start()
        logger.info("Browser manager started")

        # Initialize Twitter repository
        twitter_repo = PlaywrightTwitterRepository(browser_manager)
        logger.info("Twitter repository initialized")

        # Initialize use cases
        read_tweets_uc = ReadLastTweetsUseCase(twitter_repo)
        reply_uc = ReplyToTweetUseCase(twitter_repo)
        retweet_uc = RetweetUseCase(twitter_repo)
        post_tweet_uc = PostTweetUseCase(twitter_repo)

        # Configure route dependencies
        routes.configure_dependencies(
            read_tweets=read_tweets_uc,
            reply=reply_uc,
            retweet=retweet_uc,
            post_tweet=post_tweet_uc
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
