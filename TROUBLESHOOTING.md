# Troubleshooting Guide

## Issue: read_tweets Returns Empty Array

### Symptoms
```json
{"success":true,"tweets":[],"count":0}
```

### Common Causes and Solutions

#### 1. Tweets Not Loading (Most Common)

**Problem**: Twitter uses dynamic JavaScript loading. Tweets may not appear immediately.

**Solution**: The code now includes:
- Wait for tweet elements to appear (`wait_for_selector`)
- Additional sleep time (3 seconds) for content to render
- Scroll to trigger lazy loading

**Debug Steps**:
```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env

# Restart the API
python run_rest_api.py
```

Check logs for:
- "Tweet container found" - means tweets are detected
- "Found X tweet elements on page" - shows how many tweet elements were found
- "Tweet X: text_length=Y, id=Z" - details about each tweet

#### 2. Authentication Expired

**Problem**: Your `auth.json` session has expired.

**Solution**:
```bash
python login_and_save_auth.py
# Log in again and press Enter when you see your timeline
```

**How to verify**: Check logs for login prompts or redirects to login page.

#### 3. Twitter DOM Structure Changed

**Problem**: Twitter frequently updates their DOM structure and data-testid attributes.

**Current Selectors Used**:
- Tweet container: `article[data-testid="tweet"]`
- Tweet text: `[data-testid="tweetText"]`, `div[lang]`, `div[dir="auto"][lang]`
- Tweet links: `a[href*="/status/"]`

**Debug Steps**:

1. **Run with browser visible**:
   ```bash
   # Edit .env
   echo "BROWSER_HEADLESS=false" >> .env
   ```

2. **Check for screenshot**:
   If no tweets are found, the code saves `debug_no_tweets.png`. Check this file to see what the page looks like.

3. **Inspect Twitter manually**:
   - Open Twitter in Chromium
   - Go to a profile with tweets (e.g., https://x.com/elonmusk)
   - Right-click a tweet → Inspect
   - Look for the `<article>` element
   - Check if `data-testid="tweet"` still exists

4. **Update selectors if needed**:
   Edit [src/infrastructure/twitter_repository.py](src/infrastructure/twitter_repository.py:280) in the `_extract_tweets_from_page` method.

#### 4. Rate Limiting / Blocked

**Problem**: Twitter is rate limiting or blocking automated requests.

**Symptoms**:
- Redirects to CAPTCHA
- Access denied errors
- Empty timeline even when logged in

**Solution**:
- Use non-headless mode: `BROWSER_HEADLESS=false`
- Add delays between requests
- Ensure you're using a real browser profile (auth.json from real session)

#### 5. Wrong Username Format

**Problem**: Username has special characters or doesn't exist.

**Solution**:
```bash
# Test with a known account
curl -X POST http://localhost:8000/api/v1/read_tweets \
  -H "Content-Type: application/json" \
  -d '{"username": "twitter", "count": 3}'
```

#### 6. Insufficient Wait Time

**Problem**: Page loads but tweets haven't rendered yet.

**Current wait strategy**:
1. Wait for `domcontentloaded`
2. Wait for first tweet element (10 seconds max)
3. Sleep 3 seconds for rendering
4. Scroll to trigger more loading
5. Extract tweets

**To increase wait time**, edit [src/infrastructure/twitter_repository.py](src/infrastructure/twitter_repository.py:58):
```python
# Change from 3 to 5 seconds
await asyncio.sleep(5)
```

## Debugging Commands

### 1. Check Logs with Debug Level

```bash
# Terminal 1: Start API with debug logging
LOG_LEVEL=DEBUG python run_rest_api.py
```

### 2. Test with Browser Visible

```bash
# Edit .env
BROWSER_HEADLESS=false
LOG_LEVEL=DEBUG

# Start API
python run_rest_api.py

# In another terminal, make request
curl -X POST http://localhost:8000/api/v1/read_tweets \
  -H "Content-Type: application/json" \
  -d '{"username": "elonmusk", "count": 3}'
```

Watch the browser window to see what's happening.

### 3. Check Screenshot

If no tweets are found, check for `debug_no_tweets.png` in the project directory:

```bash
ls -la debug_no_tweets.png
# View the file to see what the page looks like
```

### 4. Verify Authentication

```bash
# Check auth.json exists and is not empty
ls -lh auth.json
cat auth.json | head -20

# If expired, re-authenticate
python login_and_save_auth.py
```

### 5. Test with Simple Profile

Some profiles are easier to scrape than others. Test with official accounts:

```bash
curl -X POST http://localhost:8000/api/v1/read_tweets \
  -H "Content-Type: application/json" \
  -d '{"username": "twitter", "count": 3}'

curl -X POST http://localhost:8000/api/v1/read_tweets \
  -H "Content-Type: application/json" \
  -d '{"username": "X", "count": 3}'
```

## Expected Log Output (Success)

When working correctly, you should see:

```
2024-12-06 12:00:00 - src.domain.use_cases - INFO - Reading last 5 tweets from @elonmusk
2024-12-06 12:00:00 - src.infrastructure.twitter_repository - INFO - Reading last 5 tweets from @elonmusk
2024-12-06 12:00:00 - src.infrastructure.twitter_repository - DEBUG - Navigating to https://x.com/elonmusk
2024-12-06 12:00:03 - src.infrastructure.twitter_repository - DEBUG - Tweet container found
2024-12-06 12:00:07 - src.infrastructure.twitter_repository - DEBUG - Found 10 tweet elements on page
2024-12-06 12:00:07 - src.infrastructure.twitter_repository - DEBUG - Tweet 0: text_length=142, id=1234567890, href=/elonmusk/status/1234567890
2024-12-06 12:00:07 - src.infrastructure.twitter_repository - INFO - Extracted tweet 1234567890: This is a tweet text...
2024-12-06 12:00:07 - src.infrastructure.twitter_repository - INFO - Successfully extracted 5 out of requested 5 tweets
```

## Expected Log Output (Failure)

### No tweets found:
```
2024-12-06 12:00:03 - src.infrastructure.twitter_repository - WARNING - No tweets found on page - user may have no tweets or page structure changed
2024-12-06 12:00:03 - src.infrastructure.twitter_repository - DEBUG - Screenshot saved to debug_no_tweets.png
2024-12-06 12:00:03 - src.infrastructure.twitter_repository - DEBUG - Found 0 tweet elements on page
2024-12-06 12:00:03 - src.infrastructure.twitter_repository - WARNING - No tweet elements found - page structure may have changed
```

### Authentication issues:
```
2024-12-06 12:00:03 - src.infrastructure.browser_manager - ERROR - Failed to start browser: Authentication file not found: auth.json
```

## Advanced Debugging: DOM Inspector Script

Create a test script to inspect the page:

```python
# test_inspect_page.py
import asyncio
from src.infrastructure.browser_manager import BrowserManager
from src.config import config

async def inspect():
    async with BrowserManager() as browser:
        page = browser.get_page()
        await page.goto("https://x.com/elonmusk")
        await asyncio.sleep(5)

        # Check for tweet elements
        tweets = await page.locator('article[data-testid="tweet"]').all()
        print(f"Found {len(tweets)} tweet elements")

        # Save full page HTML for inspection
        html = await page.content()
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved page HTML to page_debug.html")

        # Save screenshot
        await page.screenshot(path="page_debug.png", full_page=True)
        print("Saved screenshot to page_debug.png")

if __name__ == "__main__":
    asyncio.run(inspect())
```

Run it:
```bash
python test_inspect_page.py
```

Then inspect `page_debug.html` and `page_debug.png` to see exactly what the browser sees.

## Quick Fixes Summary

1. **Re-authenticate**: `python login_and_save_auth.py`
2. **Enable debug mode**: Add `LOG_LEVEL=DEBUG` to `.env`
3. **Use visible browser**: Add `BROWSER_HEADLESS=false` to `.env`
4. **Increase wait time**: Edit sleep duration in `twitter_repository.py`
5. **Check screenshot**: Look at `debug_no_tweets.png`
6. **Update selectors**: Edit `_extract_tweets_from_page` method if Twitter's DOM changed

## Still Not Working?

If tweets are still not being extracted:

1. **Check the screenshot** `debug_no_tweets.png` - this shows what the page looks like
2. **Review the HTML** - Use the DOM inspector script above
3. **Update the selectors** - Twitter may have changed their structure
4. **Open an issue** - Include:
   - Log output with `LOG_LEVEL=DEBUG`
   - Screenshot (`debug_no_tweets.png`)
   - Username you're trying to scrape
   - Whether it works in visible browser mode

## Configuration Reference

### Environment Variables (.env)

```env
# Twitter settings
TWITTER_BASE_URL=https://x.com
AUTH_STATE_PATH=auth.json

# Browser settings
BROWSER_HEADLESS=false          # Set to false for debugging
BROWSER_TIMEOUT=60000           # Increase if pages load slowly

# Logging
LOG_LEVEL=DEBUG                 # Use DEBUG for troubleshooting

# API settings
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
```

## Performance Tips

Once it's working:

1. **Use headless mode**: `BROWSER_HEADLESS=true` (faster)
2. **Reduce log level**: `LOG_LEVEL=INFO` (less verbose)
3. **Adjust timeouts**: Reduce if your network is fast
4. **Cache results**: Add caching layer if making repeated requests

## Known Limitations

1. **No timestamp parsing**: Currently uses `datetime.now()` as placeholder
2. **No engagement metrics**: Likes, retweets, replies not extracted yet
3. **Limited scroll**: Only scrolls twice, may not load all requested tweets
4. **No retweet detection**: Doesn't distinguish retweets from original tweets
5. **Rate limiting**: No built-in rate limiting (could trigger Twitter's anti-bot)

See [ARCHITECTURE.md](ARCHITECTURE.md) for implementation details.
