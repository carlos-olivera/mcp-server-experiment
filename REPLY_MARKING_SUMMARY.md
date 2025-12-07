# Reply Marking Feature - Summary

## What Was Fixed

### Problem
Originally, only the `/api/v1/reply_by_id` endpoint marked tweets/mentions as replied in MongoDB. The original `/api/v1/reply` endpoint (which uses Twitter ID) did NOT mark tweets as replied, meaning replied tweets could still appear in unanswered queries.

### Solution
Enhanced the `ReplyToTweetUseCase` to automatically mark tweets/mentions as replied in MongoDB after successful replies, regardless of which endpoint is used.

## Changes Made

### 1. Enhanced ReplyToTweetUseCase ([src/domain/use_cases.py](src/domain/use_cases.py:48-165))

**Added MongoDB Support:**
```python
def __init__(self, twitter_repo: ITwitterRepository, mongo_repo=None):
    self.twitter_repo = twitter_repo
    self.mongo_repo = mongo_repo  # Optional MongoDB repository
```

**Added Automatic Marking:**
```python
async def execute(self, tweet_id: str, text: str) -> ReplyResult:
    # ... reply on Twitter ...

    # If MongoDB is available, mark the tweet/mention as replied
    if self.mongo_repo:
        await self._mark_as_replied_in_mongodb(tweet_id, result.reply_tweet_id, text)
```

**Added Helper Methods:**
- `_mark_as_replied_in_mongodb()` - Finds and marks tweet/mention as replied
- `_log_failed_reply()` - Logs failed replies to action log

### 2. Added MongoRepository Method ([src/infrastructure/mongo_repository.py](src/infrastructure/mongo_repository.py:322-336))

```python
async def get_mention_by_twitter_id(self, tweet_id: str) -> Optional[Mention]:
    """Retrieve mention by Twitter's tweet ID."""
    doc = await self.mentions.find_one({"tweetId": tweet_id})
    if not doc:
        return None
    return self._doc_to_mention(doc)
```

### 3. Updated App Initialization ([src/api/app.py](src/api/app.py:61-63))

```python
# Now passes MongoDB repository to ReplyToTweetUseCase
reply_uc = ReplyToTweetUseCase(twitter_repo, mongo_repo)
```

## How It Works

### Endpoint 1: /api/v1/reply (Twitter ID)

```bash
curl -X POST "http://localhost:8000/api/v1/reply" \
  -H "Content-Type: application/json" \
  -d '{"tweet_id": "123456789", "text": "Reply text"}'
```

**Flow:**
1. Reply to tweet on Twitter
2. Look up tweet/mention in MongoDB by `tweetId`
3. If found, mark as replied (`repliedTo = true`)
4. Log action to audit trail

**Result:** ✅ Tweet/mention marked as replied in MongoDB

### Endpoint 2: /api/v1/reply_by_id (Internal ID)

```bash
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{"idTweet": "uuid-123", "text": "Reply text"}'
```

**Flow:**
1. Look up tweet/mention by `idTweet`
2. Reply to tweet on Twitter
3. Mark as replied in MongoDB
4. Log action to audit trail

**Result:** ✅ Tweet/mention marked as replied in MongoDB

## Benefits

### 1. Consistent Behavior
Both reply endpoints now behave the same way regarding MongoDB marking.

### 2. No Duplicates in Unanswered Queries
Once you reply to a tweet/mention, it **never** appears in:
- `GET /api/v1/mentions/unanswered`
- `GET /api/v1/mentions/unanswered?username=<user>`
- `GET /api/v1/tweets/unanswered/<username>`

### 3. Complete Audit Trail
All replies (successful and failed) logged to `actions` collection.

### 4. Optional MongoDB
MongoDB marking is optional - if tweet doesn't exist in DB, no error occurs.

## Files Changed

1. ✅ [src/domain/use_cases.py](src/domain/use_cases.py) - Enhanced ReplyToTweetUseCase
2. ✅ [src/infrastructure/mongo_repository.py](src/infrastructure/mongo_repository.py) - Added get_mention_by_twitter_id
3. ✅ [src/api/app.py](src/api/app.py) - Pass mongo_repo to ReplyToTweetUseCase

## Files Created

1. ✅ [test_reply_marking.py](test_reply_marking.py) - Automated test suite
2. ✅ [REPLY_MARKING_BEHAVIOR.md](REPLY_MARKING_BEHAVIOR.md) - Complete documentation
3. ✅ [REPLY_MARKING_SUMMARY.md](REPLY_MARKING_SUMMARY.md) - This file

## Testing

### Automated Tests

```bash
python test_reply_marking.py
```

**Tests:**
1. ✅ Reply by ID marks mention as replied
2. ✅ Reply with Twitter ID marks as replied
3. ✅ Replied mentions excluded from unanswered queries

### Manual Verification

```bash
# Get an unanswered mention
MENTIONS=$(curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=1")
ID=$(echo $MENTIONS | jq -r '.mentions[0].idTweet')

# Reply to it
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d "{\"idTweet\": \"$ID\", \"text\": \"Test\"}"

# Verify it's gone from unanswered list
curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=50" | \
  jq ".mentions[] | select(.idTweet == \"$ID\")"

# Empty output = ✅ Success
```

## MongoDB Verification

```javascript
use xserver

// Check a specific mention
db.mentions.findOne({"idTweet": "uuid-123"})

// Should show:
{
  "repliedTo": true,
  "repliedAt": ISODate("2025-12-07..."),
  "replyTweetId": "789",
  ...
}

// Check action log
db.actions.find({
  "actionType": "reply",
  "targetIdTweet": "uuid-123"
}).pretty()
```

## Backward Compatibility

✅ **Fully backward compatible**

- MongoDB parameter is optional
- If mongo_repo is None, use case works as before (Twitter only)
- If tweet not in MongoDB, no error occurs
- Existing code continues to work

## Error Handling

### If MongoDB Marking Fails

```
ERROR - Failed to mark tweet 123 as replied in MongoDB: <error>
```

**Behavior:**
- Reply still succeeds on Twitter ✅
- MongoDB not updated ❌
- Error logged but not raised

**Rationale:** Twitter reply is the primary operation

### If Reply Fails

```
ERROR - Failed to reply to tweet 123: <error>
```

**Behavior:**
- Nothing marked as replied (correct!)
- Failed action logged to MongoDB
- Exception raised to caller

## Key Points

1. **Both endpoints mark as replied** - Consistency across API
2. **Automatic and transparent** - No extra steps needed
3. **MongoDB is optional** - Works without MongoDB too
4. **Prevents duplicates** - Replied tweets never appear in unanswered queries
5. **Complete audit trail** - All replies logged
6. **Error-resilient** - MongoDB failures don't break Twitter replies

## Documentation

- **[REPLY_MARKING_BEHAVIOR.md](REPLY_MARKING_BEHAVIOR.md)** - Complete behavior guide
- **[test_reply_marking.py](test_reply_marking.py)** - Test suite with examples
- **[REPLY_MARKING_SUMMARY.md](REPLY_MARKING_SUMMARY.md)** - This summary

## Usage Example

```python
import requests

# Reply using Twitter ID (original endpoint)
response = requests.post(
    "http://localhost:8000/api/v1/reply",
    json={"tweet_id": "123456789", "text": "Thanks!"}
)

# OR reply using internal ID
response = requests.post(
    "http://localhost:8000/api/v1/reply_by_id",
    json={"idTweet": "uuid-123", "text": "Thanks!"}
)

# Either way:
# ✅ Reply posted on Twitter
# ✅ Marked as replied in MongoDB
# ✅ Won't appear in future unanswered queries
```

## Summary

**Problem:** Only one reply endpoint marked tweets as replied in MongoDB

**Solution:** Enhanced both endpoints to mark as replied

**Result:** ✅ Complete, consistent, automatic reply tracking

**Status:** ✅ Implemented, tested, and documented
