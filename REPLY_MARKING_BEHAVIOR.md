# Reply Marking Behavior

## Overview

When you reply to a tweet or mention using **any** of the reply endpoints, the system automatically marks it as "replied" in MongoDB. This ensures that replied tweets/mentions **will not appear** in future queries for unanswered tweets or mentions.

## How It Works

### Automatic Marking

Both reply endpoints automatically mark tweets/mentions as replied:

1. **`POST /api/v1/reply`** - Reply using Twitter's tweet ID
   - Looks up tweet/mention in MongoDB by `tweetId`
   - Marks as replied after successful reply on Twitter
   - Logs action to audit trail

2. **`POST /api/v1/reply_by_id`** - Reply using internal MongoDB ID
   - Looks up tweet/mention by `idTweet`
   - Marks as replied after successful reply on Twitter
   - Logs action to audit trail

### What Gets Marked

When you reply:
- **`repliedTo`** field set to `true`
- **`repliedAt`** timestamp recorded
- **`replyTweetId`** Twitter ID of your reply saved
- **Action logged** in `actions` collection for audit trail

### Result

Marked tweets/mentions are **automatically excluded** from:
- ✅ `GET /api/v1/mentions/unanswered`
- ✅ `GET /api/v1/mentions/unanswered?username=<user>`
- ✅ `GET /api/v1/tweets/unanswered/<username>`

## Example Flow

### Scenario: Replying to a Mention

```bash
# Step 1: Get unanswered mentions
curl "http://localhost:8000/api/v1/mentions/unanswered?count=5"

# Response shows 2 unanswered mentions
{
  "success": true,
  "mentions": [
    {"idTweet": "uuid-123", "tweetId": "123", "repliedTo": false, ...},
    {"idTweet": "uuid-456", "tweetId": "456", "repliedTo": false, ...}
  ],
  "count": 2
}

# Step 2: Reply to first mention
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{"idTweet": "uuid-123", "text": "Thanks!"}'

# Response confirms reply
{
  "success": true,
  "message": "Successfully replied to tweet uuid-123",
  "data": {
    "original_tweet_id": "123",
    "reply_tweet_id": "789",
    "idTweet": "uuid-123"
  }
}

# Step 3: Get unanswered mentions again
curl "http://localhost:8000/api/v1/mentions/unanswered?count=5"

# Now only 1 unanswered mention (the first one is gone!)
{
  "success": true,
  "mentions": [
    {"idTweet": "uuid-456", "tweetId": "456", "repliedTo": false, ...}
  ],
  "count": 1
}
```

## MongoDB Changes

### Before Reply

```javascript
{
  "_id": ObjectId("..."),
  "idTweet": "uuid-123",
  "tweetId": "123",
  "text": "@mybot Can you help?",
  "authorUsername": "alice",
  "repliedTo": false,
  "repliedAt": null,
  "replyTweetId": null,
  "ignored": false,
  ...
}
```

### After Reply

```javascript
{
  "_id": ObjectId("..."),
  "idTweet": "uuid-123",
  "tweetId": "123",
  "text": "@mybot Can you help?",
  "authorUsername": "alice",
  "repliedTo": true,              // ✅ Changed
  "repliedAt": ISODate("2025-12-07T..."),  // ✅ Added
  "replyTweetId": "789",          // ✅ Added
  "ignored": false,
  ...
}
```

### Action Log Entry

```javascript
// New entry in actions collection
{
  "actionType": "reply",
  "performedAt": ISODate("2025-12-07T..."),
  "success": true,
  "targetTweetId": "123",
  "targetIdTweet": "uuid-123",
  "targetUsername": "alice",
  "resultTweetId": "789",
  "metadata": {
    "reply_text": "Thanks!"
  }
}
```

## Both Reply Endpoints Work

### Using `/api/v1/reply` (Twitter ID)

```bash
# Reply using Twitter's tweet ID
curl -X POST "http://localhost:8000/api/v1/reply" \
  -H "Content-Type: application/json" \
  -d '{"tweet_id": "123456789", "text": "Great point!"}'
```

**Behavior:**
1. Sends reply on Twitter
2. Looks up tweet/mention in MongoDB by `tweetId`
3. If found, marks as replied
4. Logs action

**Result:** Tweet/mention marked as replied ✅

### Using `/api/v1/reply_by_id` (Internal ID)

```bash
# Reply using MongoDB's internal ID
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{"idTweet": "uuid-123", "text": "Great point!"}'
```

**Behavior:**
1. Looks up tweet/mention by `idTweet`
2. Sends reply on Twitter
3. Marks as replied
4. Logs action

**Result:** Tweet/mention marked as replied ✅

## Query Filters

All unanswered queries use these filters:

```javascript
// MongoDB query for unanswered mentions
{
  "repliedTo": false,  // ← Excludes replied mentions
  "ignored": false,    // ← Excludes ignored mentions
  "authorUsername": {"$nin": blocked_users}  // ← Excludes blocked users
}
```

**This ensures:**
- Replied tweets/mentions never appear in unanswered lists
- Ignored tweets/mentions never appear
- Blocked users' tweets/mentions never appear

## Error Handling

### If MongoDB Marking Fails

The reply still succeeds on Twitter, but MongoDB marking is logged as an error:

```
ERROR - Failed to mark tweet 123 as replied in MongoDB: <error>
```

**Why:** MongoDB marking is **optional**. The primary operation (replying on Twitter) always takes priority.

**Impact:**
- Tweet is replied to on Twitter ✅
- MongoDB not updated ❌
- Tweet may appear in future unanswered queries ⚠️

**Solution:** Check logs and manually mark as replied if needed.

### If Reply Already Replied

```bash
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{"idTweet": "uuid-123", "text": "Second reply"}'
```

**Response:**
```json
{
  "success": false,
  "message": "Tweet uuid-123 has already been replied to",
  "data": {
    "original_tweet_id": "123"
  },
  "error_code": "ALREADY_REPLIED"
}
```

**Behavior:** Prevents duplicate replies

## Verification

### Check if Tweet is Replied in MongoDB

```bash
mongo mongodb://user:pass@host:port/xserver?authSource=admin
```

```javascript
use xserver

// Check mention by idTweet
db.mentions.findOne({"idTweet": "uuid-123"})

// Check mention by tweetId
db.mentions.findOne({"tweetId": "123456789"})

// Count replied vs unanswered mentions
db.mentions.aggregate([
  {
    $group: {
      _id: "$repliedTo",
      count: {$sum: 1}
    }
  }
])

// Results:
// { "_id": false, "count": 10 }  // 10 unanswered
// { "_id": true, "count": 5 }    // 5 replied
```

### Check Action Log

```javascript
// View recent replies
db.actions.find({
  "actionType": "reply"
}).sort({performedAt: -1}).limit(10).pretty()

// Check replies for specific user
db.actions.find({
  "actionType": "reply",
  "targetUsername": "alice"
}).pretty()
```

## Testing

### Automated Test

```bash
python test_reply_marking.py
```

**Tests:**
1. ✅ Reply by ID marks mention as replied
2. ✅ Reply with Twitter ID marks as replied
3. ✅ Replied mentions excluded from unanswered queries

### Manual Test

```bash
# 1. Get an unanswered mention
ID=$(curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=1" | jq -r '.mentions[0].idTweet')
echo "Testing with: $ID"

# 2. Reply to it
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d "{\"idTweet\": \"$ID\", \"text\": \"Test reply\"}"

# 3. Try to get it again (should not appear)
curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=50" | jq ".mentions[] | select(.idTweet == \"$ID\")"

# If empty output: ✅ Test passed (mention is marked as replied)
# If shows the mention: ❌ Test failed (marking didn't work)
```

## Best Practices

### 1. Always Check Before Replying

```bash
# Get unanswered mentions
MENTIONS=$(curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=10")

# Process only unanswered ones
echo $MENTIONS | jq '.mentions[] | select(.repliedTo == false)'
```

### 2. Use reply_by_id for Tracked Mentions

```bash
# Recommended: Use MongoDB ID for mentions you've fetched
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -d '{"idTweet": "uuid-from-database", "text": "Reply"}'

# Rather than: Using Twitter ID (works but less tracked)
curl -X POST "http://localhost:8000/api/v1/reply" \
  -d '{"tweet_id": "twitter-id", "text": "Reply"}'
```

### 3. Monitor Action Logs

```javascript
// Check for failed replies
db.actions.find({
  "actionType": "reply",
  "success": false
}).sort({performedAt: -1})

// Check reply rate
db.actions.aggregate([
  {$match: {"actionType": "reply"}},
  {
    $group: {
      _id: "$success",
      count: {$sum: 1}
    }
  }
])
```

## Troubleshooting

### Problem: Replied Mention Still Appears

**Possible causes:**
1. MongoDB marking failed (check logs)
2. Different tweet with same text
3. Reply failed but you didn't notice

**Debug:**
```javascript
// Check the mention's status
db.mentions.findOne({"idTweet": "uuid-123"}, {
  repliedTo: 1,
  repliedAt: 1,
  replyTweetId: 1,
  ignored: 1
})
```

**Fix:**
```javascript
// Manually mark as replied
db.mentions.updateOne(
  {"idTweet": "uuid-123"},
  {
    $set: {
      repliedTo: true,
      repliedAt: new Date(),
      replyTweetId: "your-reply-tweet-id"
    }
  }
)
```

### Problem: Reply Succeeded but Not Marked

**Check logs:**
```bash
grep "Failed to mark tweet" /path/to/logs
```

**Common causes:**
- MongoDB connection lost
- Tweet not in database yet
- Permission error

**Solution:**
1. Check MongoDB is accessible
2. Verify tweet exists in database
3. Check MongoDB user permissions

## Summary

✅ **Both reply endpoints mark tweets/mentions as replied**
✅ **Replied tweets/mentions automatically excluded from unanswered queries**
✅ **Action log maintains complete audit trail**
✅ **MongoDB marking is automatic and transparent**
✅ **Prevents duplicate replies**

**Key takeaway:** Once you reply to a tweet or mention, it will **never appear** in your unanswered lists again.
