# Quick Start Guide - MongoDB Integration

## What's New

The Twitter MCP Agent now includes:
- ✅ **MongoDB persistence** for all tweets, mentions, and actions
- ✅ **Abuse prevention** - Auto-blocks users after 10 ignored mentions
- ✅ **New endpoints** for unanswered mentions and tweets
- ✅ **Internal IDs** (`idTweet`) for referencing tweets

## Prerequisites

1. **MongoDB server** running at `192.168.50.139:27017` (configurable via `.env`)
2. **Python 3.8+** with virtual environment
3. **Twitter authentication** (`auth.json` file)

## Installation

```bash
# 1. Install dependencies (including new MongoDB drivers)
pip install -r requirements.txt

# 2. Install Playwright browser
playwright install chromium

# 3. Authenticate with Twitter (if you haven't already)
python login_and_save_auth.py
```

## Configuration

The `.env` file now includes MongoDB settings:

```env
# MongoDB Configuration
MONGO_USER=criptoUser
MONGO_PASSWORD=criptoPass456
MONGO_HOST=192.168.50.139
MONGO_PORT=27017
MONGO_DB=xserver
MONGO_AUTH_SOURCE=admin

# Abuse Prevention
MAX_MENTIONS_PER_USER_IN_BATCH=1
MAX_IGNORED_BEFORE_BLOCK=10
```

## Running the API

```bash
python run_rest_api.py
```

On startup, you'll see:
```
INFO - Initializing MongoDB connection
INFO - MongoDB connected to 192.168.50.139:27017/xserver
INFO - Browser manager started
INFO - REST API startup complete
```

## New Endpoints

### 1. Get Unanswered Mentions

**Request:**
```bash
curl "http://localhost:8000/api/v1/mentions/unanswered?count=5"
```

**Response:**
```json
{
  "success": true,
  "mentions": [
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440000",
      "tweetId": "1234567890",
      "text": "@mybot Please help!",
      "authorUsername": "user123",
      "createdAt": "2024-12-06T12:00:00",
      "url": "https://x.com/user123/status/1234567890",
      "type": "mention",
      "repliedTo": false,
      "ignored": false,
      "mentionedUsers": ["@mybot"]
    }
  ],
  "count": 1
}
```

**Features:**
- Fetches recent mentions from Twitter
- Stores in MongoDB with unique `idTweet`
- Filters duplicates (max 1 per user per batch)
- Auto-ignores extras and blocks abusive users

### 2. Get Unanswered Tweets from User

**Request:**
```bash
curl "http://localhost:8000/api/v1/tweets/unanswered/elonmusk?count=5"
```

**Response:**
```json
{
  "success": true,
  "tweets": [
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440001",
      "tweetId": "1234567891",
      "text": "Interesting development in AI",
      "authorUsername": "elonmusk",
      "createdAt": "2024-12-06T13:00:00",
      "url": "https://x.com/elonmusk/status/1234567891",
      "type": "regular",
      "repliedTo": false,
      "ignored": false
    }
  ],
  "count": 1,
  "username": "elonmusk"
}
```

### 3. Reply by Internal ID

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{
    "idTweet": "550e8400-e29b-41d4-a716-446655440000",
    "text": "Thanks for reaching out!"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully replied to tweet 550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "original_tweet_id": "1234567890",
    "reply_tweet_id": "1234567892",
    "idTweet": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**What happens:**
1. Looks up tweet in MongoDB by `idTweet`
2. Posts reply on Twitter
3. Marks as replied in MongoDB
4. Logs action in audit trail

### 4. Post Tweet (Enhanced)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/post_tweet" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Twitter MCP Agent with MongoDB!"}'
```

## MongoDB Collections

The API automatically creates these collections:

### `tweets`
- All regular tweets we've interacted with
- Tracks if we've replied, retweeted, or ignored

### `mentions`
- All mentions of our account
- Includes `mentionedUsers` array
- Tracks abuse prevention

### `blocked_users`
- Users blocked due to excessive mentions
- Auto-populated when user reaches 10 ignored mentions

### `actions`
- Complete audit log of all actions
- Includes: reply, repost, post, ignore, block

## Abuse Prevention Flow

```
User @spammer mentions you 5 times
  ↓
GET /mentions/unanswered?count=5
  ↓
Returns 1 mention from @spammer
Ignores other 4 with reason "duplicate_user"
  ↓
@spammer mentions you 6 more times
  ↓
GET /mentions/unanswered?count=5
  ↓
Returns 1 mention from @spammer
Total ignored reaches 10
  ↓
@spammer is automatically added to blocked_users
  ↓
Future calls exclude @spammer entirely
```

## Workflow Example

### Responding to Mentions

```bash
# Step 1: Get unanswered mentions
MENTIONS=$(curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=5")
echo $MENTIONS | jq '.mentions[]'

# Step 2: Extract first mention's idTweet
ID_TWEET=$(echo $MENTIONS | jq -r '.mentions[0].idTweet')

# Step 3: Reply to that mention
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d "{
    \"idTweet\": \"$ID_TWEET\",
    \"text\": \"Thanks for your message!\"
  }"
```

### Monitoring a User's Tweets

```bash
# Get unanswered tweets from specific user
curl "http://localhost:8000/api/v1/tweets/unanswered/elonmusk?count=10" | jq '.'

# Reply to interesting ones using their idTweet
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{
    "idTweet": "<id from previous call>",
    "text": "Interesting point!"
  }'
```

## Checking MongoDB Data

```bash
# Connect to MongoDB
mongo mongodb://criptoUser:criptoPass456@192.168.50.139:27017/xserver?authSource=admin

# View mentions
db.mentions.find().pretty()

# Count unanswered mentions
db.mentions.countDocuments({repliedTo: false, ignored: false})

# View blocked users
db.blocked_users.find().pretty()

# View recent actions
db.actions.find().sort({performedAt: -1}).limit(10).pretty()
```

## Troubleshooting

### MongoDB Connection Issues

**Error:** `MongoDB connection failed`

**Solution:**
1. Check MongoDB is running: `ping 192.168.50.139`
2. Verify credentials in `.env`
3. Check firewall allows port 27017

### No Mentions Found

**Issue:** `/mentions/unanswered` returns empty array

**Reasons:**
- No new mentions on Twitter
- All mentions already replied to
- All mention authors are blocked

**Debug:**
```bash
# Check MongoDB directly
mongo ...
db.mentions.find({}).count()  # Total mentions
db.mentions.find({repliedTo: false}).count()  # Unanswered
db.blocked_users.find({}).count()  # Blocked users
```

### Tweet Already Replied

**Error:** `Tweet has already been replied to`

**Solution:** This is expected - the system prevents duplicate replies. Check MongoDB:
```javascript
db.mentions.findOne({idTweet: "<your-id>"})
// Look at repliedTo field
```

## API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Architecture

For detailed architecture information, see:
- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete system design
- [MONGODB_SCHEMA.md](MONGODB_SCHEMA.md) - Database schema details
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Implementation details

## Next Steps

1. **Test the new endpoints** with your Twitter account
2. **Monitor MongoDB** to see data being stored
3. **Adjust abuse thresholds** in `.env` if needed
4. **Set up automation** to periodically check mentions
5. **Add error handling** for your specific use case

## Support

- Check logs: The API logs all operations with DEBUG level available
- MongoDB queries: Use the mongo shell to inspect data
- Issues: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
