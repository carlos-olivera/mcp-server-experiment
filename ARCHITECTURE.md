# Twitter MCP Agent - Architecture Documentation

## Overview

This project implements a **Twitter automation agent** accessible via both **MCP (Model Context Protocol)** and **REST API**. It follows **clean architecture principles** with clear separation of concerns across layers.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    External Clients                          │
│              (MCP Clients / HTTP Clients)                    │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴────────────────┐
            │                                │
    ┌───────▼────────┐              ┌───────▼────────┐
    │   MCP Layer    │              │   API Layer    │
    │  (FastMCP)     │              │   (FastAPI)    │
    │                │              │                │
    │  - Tools       │              │  - Routes      │
    │  - Server      │              │  - Schemas     │
    └───────┬────────┘              └───────┬────────┘
            │                                │
            └───────────────┬────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │   Domain Layer    │
                  │  (Business Logic) │
                  │                   │
                  │  - Use Cases      │
                  │  - Models         │
                  │  - Interfaces     │
                  └─────────┬─────────┘
                            │
                ┌───────────▼────────────┐
                │  Infrastructure Layer  │
                │  (Technical Details)   │
                │                        │
                │  - TwitterRepository   │
                │  - BrowserManager      │
                │  - Logging Config      │
                └───────────┬────────────┘
                            │
                  ┌─────────▼─────────┐
                  │     Playwright    │
                  │  (Chromium/Web)   │
                  └───────────────────┘
```

## Layer Details

### 1. Domain Layer (`src/domain/`)

**Purpose**: Pure business logic, framework-agnostic

**Components**:
- **`models.py`**: Data models (Tweet, ActionResult, etc.)
  - Simple dataclasses representing business entities
  - JSON-serializable via `to_dict()` methods

- **`interfaces.py`**: Port interfaces for dependency inversion
  - `ITwitterRepository`: Abstract interface for Twitter operations
  - `TwitterRepositoryError`: Domain exception

- **`use_cases.py`**: Business use cases
  - `ReadLastTweetsUseCase`: Orchestrates reading tweets
  - `ReplyToTweetUseCase`: Orchestrates replying
  - `RetweetUseCase`: Orchestrates retweeting
  - `PostTweetUseCase`: Orchestrates posting
  - Each use case contains validation and logging

**Key Principles**:
- No dependencies on frameworks (FastAPI, Playwright, etc.)
- Pure Python business logic
- Dependency inversion via interfaces

### 2. Infrastructure Layer (`src/infrastructure/`)

**Purpose**: External integrations and technical implementations

**Components**:
- **`browser_manager.py`**: Playwright browser lifecycle management
  - Starts/stops browser
  - Loads Twitter session from `auth.json`
  - Provides page instances to repository
  - Implements context manager pattern

- **`twitter_repository.py`**: Playwright-based Twitter implementation
  - Implements `ITwitterRepository` interface
  - Uses DOM selectors and page navigation
  - Handles Playwright-specific errors
  - Translates web interactions to domain models

- **`logging_config.py`**: Structured logging setup
  - Configures Python logging
  - Sets log levels for different components
  - Provides logger factory

**Key Principles**:
- Implements domain interfaces
- Handles all external I/O
- Converts technical details to domain models

### 3. API Layer (`src/api/`)

**Purpose**: REST API using FastAPI

**Components**:
- **`app.py`**: FastAPI application setup
  - Creates FastAPI instance
  - Manages application lifespan (startup/shutdown)
  - Initializes dependencies (browser, repository, use cases)
  - Configures global exception handling

- **`routes.py`**: HTTP endpoints
  - `POST /api/v1/read_tweets`: Read tweets from a user
  - `POST /api/v1/reply`: Reply to a tweet
  - `POST /api/v1/retweet`: Retweet a tweet
  - `POST /api/v1/post_tweet`: Post a new tweet
  - `GET /api/v1/health`: Health check

- **`schemas.py`**: Pydantic request/response models
  - Request validation
  - Response serialization
  - API documentation

**Key Principles**:
- Only handles HTTP concerns
- Delegates to use cases
- Returns JSON responses
- Proper error handling with status codes

### 4. MCP Layer (`src/mcp/`)

**Purpose**: MCP server using FastMCP

**Components**:
- **`server.py`**: MCP server implementation
  - Defines MCP tools (read_last_tweets, reply_to_tweet, etc.)
  - Maps tool calls to use cases
  - Handles initialization and cleanup
  - Returns JSON-serializable results

**Key Principles**:
- Tools are thin wrappers around use cases
- Consistent error handling
- Proper logging

### 5. Configuration (`src/config.py`)

**Purpose**: Centralized configuration management

**Features**:
- Loads from environment variables (`.env`)
- Provides defaults
- Configuration validation
- Type-safe access to settings

**Settings**:
- `TWITTER_BASE_URL`: Twitter/X base URL
- `AUTH_STATE_PATH`: Path to auth.json
- `BROWSER_HEADLESS`: Headless mode flag
- `BROWSER_TIMEOUT`: Page load timeout
- `HTTP_HOST`, `HTTP_PORT`: REST API settings
- `LOG_LEVEL`: Logging verbosity

## Data Flow

### REST API Request Flow

```
HTTP Request
    ↓
FastAPI Route (routes.py)
    ↓
Request Validation (schemas.py)
    ↓
Use Case Execution (use_cases.py)
    ↓
Repository Call (twitter_repository.py)
    ↓
Playwright Browser Action
    ↓
Domain Model Creation
    ↓
Response Serialization
    ↓
HTTP Response (JSON)
```

### MCP Tool Call Flow

```
MCP Tool Call
    ↓
MCP Server (server.py)
    ↓
Use Case Execution (use_cases.py)
    ↓
Repository Call (twitter_repository.py)
    ↓
Playwright Browser Action
    ↓
Domain Model Creation
    ↓
Dictionary Response
    ↓
MCP Tool Result
```

## Running the Application

### Prerequisites

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Authenticate with Twitter**:
   ```bash
   python login_and_save_auth.py
   ```
   This creates `auth.json` with your session.

3. **Configure environment** (optional):
   Edit `.env` to customize settings.

### Run REST API Server

```bash
python run_rest_api.py
```

The API will be available at `http://localhost:8000`.

**API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger UI.

### Run MCP Server

```bash
python run_mcp_server.py
```

The MCP server will start and be accessible via MCP clients.

## API Usage Examples

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Read Tweets

```bash
curl -X POST http://localhost:8000/api/v1/read_tweets \
  -H "Content-Type: application/json" \
  -d '{
    "username": "elonmusk",
    "count": 5
  }'
```

**Response**:
```json
{
  "success": true,
  "tweets": [
    {
      "id": "1234567890",
      "text": "Tweet content here...",
      "author_username": "elonmusk",
      "url": "https://x.com/elonmusk/status/1234567890",
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "count": 5
}
```

### Reply to Tweet

```bash
curl -X POST http://localhost:8000/api/v1/reply \
  -H "Content-Type: application/json" \
  -d '{
    "tweet_id": "1234567890",
    "text": "Great point!"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Successfully replied to tweet 1234567890",
  "data": {
    "original_tweet_id": "1234567890",
    "reply_text": "Great point!"
  }
}
```

### Retweet

```bash
curl -X POST http://localhost:8000/api/v1/retweet \
  -H "Content-Type: application/json" \
  -d '{
    "tweet_id": "1234567890"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Successfully retweeted tweet 1234567890",
  "data": {
    "tweet_id": "1234567890"
  }
}
```

### Post Tweet

```bash
curl -X POST http://localhost:8000/api/v1/post_tweet \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from the Twitter MCP Agent!"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Successfully posted tweet",
  "data": {
    "tweet_text": "Hello from the Twitter MCP Agent!"
  }
}
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE"
}
```

**Common Error Codes**:
- `VALIDATION_ERROR`: Invalid input parameters
- `TIMEOUT`: Browser operation timeout
- `READ_FAILED`: Failed to read tweets
- `REPLY_FAILED`: Failed to reply
- `RETWEET_FAILED`: Failed to retweet
- `POST_FAILED`: Failed to post tweet
- `INTERNAL_ERROR`: Unexpected server error

**HTTP Status Codes**:
- `200`: Success
- `400`: Bad request (validation error)
- `500`: Internal server error
- `503`: Service unavailable (Twitter operation failed)

## Logging

The application uses structured logging with the following levels:

- **DEBUG**: Detailed browser operations, selectors, navigation
- **INFO**: Request/response logs, successful operations
- **WARNING**: Timeouts that are handled, deprecation warnings
- **ERROR**: Failed operations, exceptions

**Log format**:
```
2024-01-01 12:00:00 - module.name - INFO - Log message
```

**Configure logging**:
Set `LOG_LEVEL` in `.env`:
```env
LOG_LEVEL=DEBUG
```

## Security Considerations

1. **`auth.json` is sensitive**: Contains Twitter session cookies
   - Keep it out of version control (already in `.gitignore`)
   - Treat it as a secret

2. **No sensitive data in logs**: The application avoids logging credentials or session data

3. **Input validation**: All user inputs are validated via Pydantic schemas

4. **Error messages**: Don't expose internal implementation details to clients

## Testing Strategy

### Manual Testing

1. **Test authentication**:
   ```bash
   python login_and_save_auth.py
   ```

2. **Test browser manager**:
   ```bash
   python test_agent.py
   ```

3. **Test REST API**:
   - Start server: `python run_rest_api.py`
   - Use curl or Postman to test endpoints

### Future Automated Testing

**Unit Tests** (recommended):
- Test use cases with mock repositories
- Test domain models
- Test validation logic

**Integration Tests** (recommended):
- Test API endpoints with test database
- Test MCP tools

**Example structure**:
```
tests/
├── unit/
│   ├── test_use_cases.py
│   └── test_models.py
├── integration/
│   ├── test_api.py
│   └── test_mcp.py
└── conftest.py
```

## Extending the Application

### Adding a New Twitter Action

1. **Add domain model** in `src/domain/models.py`
2. **Add interface method** in `src/domain/interfaces.py`
3. **Implement in repository** in `src/infrastructure/twitter_repository.py`
4. **Create use case** in `src/domain/use_cases.py`
5. **Add API endpoint** in `src/api/routes.py`
6. **Add MCP tool** in `src/mcp/server.py`

### Adding a New Transport Layer

The architecture supports adding new transport layers (e.g., gRPC, WebSocket):

1. Create new layer directory (e.g., `src/grpc/`)
2. Import and use domain use cases
3. Handle transport-specific concerns
4. Map to domain models

## Dependencies

See [requirements.txt](requirements.txt) for full list:

- **fastmcp**: MCP server framework
- **fastapi**: REST API framework
- **uvicorn**: ASGI server
- **playwright**: Browser automation
- **python-dotenv**: Environment variable management
- **pydantic**: Data validation

## Project Structure

```
twitter-mcp-agent/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Configuration
│   ├── domain/                      # Business logic
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── interfaces.py
│   │   └── use_cases.py
│   ├── infrastructure/              # External integrations
│   │   ├── __init__.py
│   │   ├── browser_manager.py
│   │   ├── twitter_repository.py
│   │   └── logging_config.py
│   ├── api/                         # REST API
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   └── schemas.py
│   └── mcp/                         # MCP server
│       ├── __init__.py
│       └── server.py
├── login_and_save_auth.py          # Auth utility
├── run_rest_api.py                 # REST API entry point
├── run_mcp_server.py               # MCP server entry point
├── test_agent.py                   # Simple test
├── requirements.txt
├── .env                            # Configuration
├── .gitignore
├── ARCHITECTURE.md                 # This file
└── README.md
```

## Troubleshooting

### Browser won't start
- Ensure Playwright is installed: `playwright install chromium`
- Check `auth.json` exists: `python login_and_save_auth.py`

### Twitter actions fail
- Session may have expired - re-run `login_and_save_auth.py`
- Twitter's DOM may have changed - update selectors in `twitter_repository.py`
- Check logs for detailed error messages

### API returns 503
- Browser operations timed out
- Twitter is unavailable
- Check browser headless mode: set `BROWSER_HEADLESS=false` for debugging

## Contributing

When contributing, maintain the clean architecture:

1. **Domain logic** should never import from infrastructure/api/mcp
2. **Use cases** should be pure orchestration
3. **Infrastructure** implements domain interfaces
4. **Transport layers** (API/MCP) only handle I/O concerns
5. Add proper logging and error handling
6. Update this documentation

## License

MIT License - see [LICENSE](LICENSE) file for details
