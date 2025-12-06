# Twitter MCP Agent Experiment

A clean architecture implementation of a Twitter automation agent accessible via both **MCP (Model Context Protocol)** and **REST API**.

## Features

- **Read tweets** from any user's profile
- **Reply to tweets** by ID
- **Retweet** (repost) tweets
- **Post new tweets**
- **Dual interface**: MCP server + REST API
- **Clean architecture** with proper separation of concerns
- **Structured logging** for observability
- **Browser automation** via Playwright

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### 2. Authenticate with Twitter

```bash
python login_and_save_auth.py
```

This will open a Chromium browser. Log in to Twitter/X and press Enter when you see your timeline. This creates `auth.json` with your session.

### 3. Run the REST API

```bash
python run_rest_api.py
```

The API will be available at `http://localhost:8000`.

**Interactive docs**: Visit `http://localhost:8000/docs`

### 4. Or Run the MCP Server

```bash
python run_mcp_server.py
```

## Usage Examples

### REST API

**Read tweets**:
```bash
curl -X POST http://localhost:8000/api/v1/read_tweets \
  -H "Content-Type: application/json" \
  -d '{"username": "elonmusk", "count": 5}'
```

**Post a tweet**:
```bash
curl -X POST http://localhost:8000/api/v1/post_tweet \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Twitter MCP Agent!"}'
```

**Reply to a tweet**:
```bash
curl -X POST http://localhost:8000/api/v1/reply \
  -H "Content-Type: application/json" \
  -d '{"tweet_id": "1234567890", "text": "Great point!"}'
```

**Retweet**:
```bash
curl -X POST http://localhost:8000/api/v1/retweet \
  -H "Content-Type: application/json" \
  -d '{"tweet_id": "1234567890"}'
```

### MCP

The MCP server exposes the following tools:
- `read_last_tweets(username, count)`
- `reply_to_tweet(tweet_id, text)`
- `retweet(tweet_id)`
- `post_tweet(text)`

## Configuration

Edit `.env` to customize settings:

```env
TWITTER_BASE_URL=https://x.com
AUTH_STATE_PATH=auth.json
BROWSER_HEADLESS=false
BROWSER_TIMEOUT=60000
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
LOG_LEVEL=INFO
```

## Architecture

This project follows **clean architecture** principles with four main layers:

1. **Domain Layer** - Pure business logic (use cases, models, interfaces)
2. **Infrastructure Layer** - External integrations (Playwright, browser management)
3. **API Layer** - REST API using FastAPI
4. **MCP Layer** - MCP server using FastMCP

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

## Project Structure

```
twitter-mcp-agent/
├── src/
│   ├── domain/          # Business logic
│   ├── infrastructure/  # Playwright, browser, logging
│   ├── api/             # FastAPI routes and schemas
│   └── mcp/             # MCP server and tools
├── login_and_save_auth.py
├── run_rest_api.py
├── run_mcp_server.py
└── requirements.txt
```

## Security

- **`auth.json` contains your Twitter session** - keep it secret!
- Already added to `.gitignore`
- Don't commit it to version control

## Troubleshooting

### Quick Fixes

**Browser won't start?**
```bash
playwright install chromium
```

**Session expired?**
```bash
python login_and_save_auth.py
```

**Enable debug mode:**
```env
LOG_LEVEL=DEBUG
BROWSER_HEADLESS=false
```

### read_tweets Returns Empty Array?

If you get `{"success":true,"tweets":[],"count":0}`:

**Quick test:**
```bash
# Run the debugging script
python test_tweet_extraction.py elonmusk 5
```

This will:
- Open browser visibly
- Show detailed logs
- Save screenshots if tweets aren't found
- Help identify the issue

**Common causes:**
1. **Authentication expired** - Run `python login_and_save_auth.py` again
2. **Twitter DOM changed** - Check logs for warnings about selectors
3. **Page not loaded** - Increase `BROWSER_TIMEOUT` in `.env`

**For detailed troubleshooting**, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Development

### Run Tests
```bash
# Manual test
python test_agent.py
```

### Add New Features

1. Add domain model in `src/domain/models.py`
2. Add interface method in `src/domain/interfaces.py`
3. Implement in `src/infrastructure/twitter_repository.py`
4. Create use case in `src/domain/use_cases.py`
5. Add API endpoint in `src/api/routes.py`
6. Add MCP tool in `src/mcp/server.py`

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions welcome! Please maintain the clean architecture principles:
- Domain layer should not depend on frameworks
- Use dependency inversion
- Add proper logging and error handling
