# Quote Tweet Feature

## Overview

The `reply_by_id` endpoint now supports **quote tweets** (retweets with comments) in addition to regular replies. By setting the `quoted` parameter to `true`, you can share a tweet with your own commentary on your timeline.

## What is a Quote Tweet?

A quote tweet (also called "retweet with comment") allows you to:
- Share the original tweet with your followers
- Add your own commentary or context above the embedded tweet
- Post to your own timeline (not just as a threaded reply)

### Quote Tweet vs Reply

| Feature | Reply (`quoted: false`) | Quote Tweet (`quoted: true`) |
|---------|------------------------|------------------------------|
| **Appearance** | Appears in thread below original | Appears on your timeline with original embedded |
| **Visibility** | Mainly seen by original author and followers | Seen by your followers |
| **Use Case** | Direct response to author | Share with commentary |
| **Format** | Standard threaded reply | Your text + embedded original tweet |

## API Usage

### Endpoint

```
POST /api/v1/reply_by_id
```

### Request Body

```json
{
  "idTweet": "550e8400-e29b-41d4-a716-446655440000",
  "text": "This is brilliant! Adding my thoughts here.",
  "quoted": true
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `idTweet` | string | Yes | - | Internal MongoDB UUID of the tweet |
| `text` | string | Yes | - | Your comment text (max 280 characters) |
| `quoted` | boolean | No | `false` | If `true`, post as quote tweet; if `false`, post as regular reply |

### Response

#### Success (Quote Tweet)

```json
{
  "success": true,
  "message": "Successfully quote tweeted tweet 550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "success": true,
    "message": "Successfully quote tweeted tweet 550e8400-e29b-41d4-a716-446655440000",
    "data": {
      "idTweet": "550e8400-e29b-41d4-a716-446655440000",
      "quoted": true
    },
    "error_code": null,
    "original_tweet_id": "1734567890123456789",
    "reply_tweet_id": "1734567890123456792"
  }
}
```

#### Success (Regular Reply)

```json
{
  "success": true,
  "message": "Successfully replied to tweet 550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "success": true,
    "message": "Successfully replied to tweet 550e8400-e29b-41d4-a716-446655440000",
    "data": {
      "idTweet": "550e8400-e29b-41d4-a716-446655440000",
      "quoted": false
    },
    "error_code": null,
    "original_tweet_id": "1734567890123456789",
    "reply_tweet_id": "1734567890123456791"
  }
}
```

## Examples

### Example 1: Regular Reply

```bash
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{
    "idTweet": "uuid-from-database",
    "text": "Thanks for this!"
  }'
```

**Result:** Standard threaded reply under the original tweet.

### Example 2: Quote Tweet

```bash
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d '{
    "idTweet": "uuid-from-database",
    "text": "This is a great insight! Here are my thoughts...",
    "quoted": true
  }'
```

**Result:** Your tweet appears on your timeline with the original tweet embedded below your comment.

### Example 3: Quote Tweet for Amplification

```bash
# Get an interesting tweet first
TWEET_ID=$(curl -s "http://localhost:8000/api/v1/tweets/unanswered/elonmusk?count=1" | jq -r '.tweets[0].idTweet')

# Quote tweet it with your perspective
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d "{
    \"idTweet\": \"$TWEET_ID\",
    \"text\": \"Fascinating perspective on AI! This aligns with what we're seeing in our research.\",
    \"quoted\": true
  }"
```

## MongoDB Behavior

### Marking as Replied

Both quote tweets and regular replies mark the original tweet/mention as "replied" in MongoDB:

```javascript
{
  "repliedTo": true,
  "repliedAt": ISODate("2025-12-07T..."),
  "replyTweetId": "1734567890123456792"
}
```

This ensures the tweet **won't appear** in future unanswered queries, regardless of whether you used quote tweet or regular reply.

### Action Logging

Quote tweets are logged with `actionType: "quote_tweet"`:

```javascript
// Regular reply action log
{
  "actionType": "reply",
  "performedAt": ISODate("2025-12-07T..."),
  "success": true,
  "targetTweetId": "1734567890123456789",
  "targetIdTweet": "uuid-123",
  "targetUsername": "alice",
  "resultTweetId": "1734567890123456791",
  "metadata": {
    "text": "Thanks!",
    "quoted": false
  }
}

// Quote tweet action log
{
  "actionType": "quote_tweet",
  "performedAt": ISODate("2025-12-07T..."),
  "success": true,
  "targetTweetId": "1734567890123456789",
  "targetIdTweet": "uuid-123",
  "targetUsername": "alice",
  "resultTweetId": "1734567890123456792",
  "metadata": {
    "text": "Great insight!",
    "quoted": true
  }
}
```

This allows you to track:
- How many replies vs quote tweets you've posted
- Which tweets you amplified vs directly replied to
- Success/failure rates for each action type

## Use Cases

### When to Use Quote Tweet

1. **Amplifying Content**
   - Share interesting tweets with your followers
   - Boost visibility of important messages
   - Add your endorsement or context

2. **Adding Commentary**
   - Provide expert analysis on a topic
   - Share a different perspective
   - Add context your followers need

3. **Building Engagement**
   - Start a conversation on your timeline
   - Share content relevant to your audience
   - Participate in trending discussions

### When to Use Regular Reply

1. **Direct Response**
   - Answer a question posed to you
   - Respond to a mention
   - Continue a conversation thread

2. **Private Conversation**
   - Keep discussion in the thread
   - Respond without broadcasting to all followers

3. **Quick Acknowledgment**
   - Simple "thanks" or "agree"
   - Direct feedback to the author

## Implementation Details

### How It Works (Playwright Automation)

When `quoted: true`, the system:

1. **Navigates** to the tweet URL
2. **Clicks** the retweet button
3. **Selects** "Quote" from the dropdown menu
4. **Fills** the comment text in the composer
5. **Clicks** the post button
6. **Marks** as replied in MongoDB
7. **Logs** action as "quote_tweet"

```python
# Simplified flow
if quoted:
    # Click retweet button
    await page.locator('[data-testid="retweet"]').first.click()

    # Select Quote option
    await page.locator('[data-testid="Dropdown"] [role="menuitem"]')
        .filter(has_text="Quote").first.click()

    # Fill comment
    await page.locator('[data-testid="tweetTextarea_0"]').first.fill(text)

    # Post
    await page.locator('[data-testid="tweetButton"]').first.click()
else:
    # Standard reply flow
    await page.locator('[data-testid="reply"]').first.click()
    # ... etc
```

## Error Handling

### Already Replied

If a tweet has already been replied to (regular reply or quote tweet), attempting either action will fail:

```json
{
  "success": false,
  "message": "Tweet uuid-123 has already been replied to",
  "data": {
    "original_tweet_id": "1734567890123456789"
  },
  "error_code": "ALREADY_REPLIED"
}
```

**Note:** This prevents duplicate quote tweets even if the original was a regular reply (and vice versa).

### Not Found

If the `idTweet` doesn't exist in MongoDB:

```json
{
  "detail": {
    "success": false,
    "error": "Tweet not found with idTweet=invalid-id",
    "error_code": "NOT_FOUND"
  }
}
```

### Twitter API Errors

If Twitter rejects the quote tweet:

```json
{
  "detail": {
    "success": false,
    "error": "Failed to quote tweet: <error details>",
    "error_code": "QUOTE_FAILED"
  }
}
```

## Testing

### Test Quote Tweet

```bash
# 1. Get an unanswered mention
MENTION=$(curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=1")
ID=$(echo $MENTION | jq -r '.mentions[0].idTweet')

echo "Testing quote tweet for: $ID"

# 2. Quote tweet it
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d "{
    \"idTweet\": \"$ID\",
    \"text\": \"[TEST] Quote tweet test\",
    \"quoted\": true
  }" | jq

# 3. Verify it's marked as replied
curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=50" | \
  jq ".mentions[] | select(.idTweet == \"$ID\")"

# If empty: ✅ Quote tweet worked and marked as replied
# If shows mention: ❌ Something failed
```

### Compare Reply vs Quote Tweet

```bash
# Get two unanswered mentions
MENTIONS=$(curl -s "http://localhost:8000/api/v1/mentions/unanswered?count=2")
ID1=$(echo $MENTIONS | jq -r '.mentions[0].idTweet')
ID2=$(echo $MENTIONS | jq -r '.mentions[1].idTweet')

echo "Reply test: $ID1"
echo "Quote tweet test: $ID2"

# Regular reply
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d "{
    \"idTweet\": \"$ID1\",
    \"text\": \"Thanks for the mention!\",
    \"quoted\": false
  }"

# Quote tweet
curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
  -H "Content-Type: application/json" \
  -d "{
    \"idTweet\": \"$ID2\",
    \"text\": \"Great question! Let me share this with my followers.\",
    \"quoted\": true
  }"

# Check action logs
mongo mongodb://user:pass@host/xserver?authSource=admin --eval '
  db.actions.find({
    $or: [
      {targetIdTweet: "'$ID1'"},
      {targetIdTweet: "'$ID2'"}
    ]
  }).sort({performedAt: -1}).pretty()
'
```

## Postman Collection

The Postman collection includes:

1. **Reply by Internal ID** - Regular reply example with `quoted: false`
2. **Quote Tweet by Internal ID** - Quote tweet example with `quoted: true`

Import `Twitter_MCP_Agent.postman_collection.json` to test both endpoints.

## Best Practices

### 1. Choose the Right Action

```python
# Use quote tweet for amplification
if want_to_share_with_followers:
    quoted = True
    text = "Check out this insight from @user!"

# Use reply for direct response
else:
    quoted = False
    text = "@user Thanks for the question!"
```

### 2. Monitor Action Types

```javascript
// Track quote tweet rate
db.actions.aggregate([
  {$match: {actionType: {$in: ["reply", "quote_tweet"]}}},
  {$group: {
    _id: "$actionType",
    count: {$sum: 1}
  }}
])

// Results:
// { "_id": "reply", "count": 45 }
// { "_id": "quote_tweet", "count": 12 }
```

### 3. Avoid Spam

- Don't quote tweet every mention (use sparingly)
- Add meaningful commentary, not just generic text
- Mix quote tweets with regular replies

### 4. Track Engagement

```javascript
// Find your most amplified tweets (quote tweets)
db.actions.find({
  actionType: "quote_tweet",
  success: true
}).sort({performedAt: -1}).limit(10)
```

## Troubleshooting

### Problem: Quote Tweet Doesn't Appear on Timeline

**Possible causes:**
- Twitter may have rate limits
- Account may be restricted
- Text may violate Twitter policies

**Debug:**
1. Check logs for errors
2. Try regular reply first
3. Verify account status on Twitter

### Problem: Wrong Action Type in Logs

**Check:**
```javascript
db.actions.findOne({targetIdTweet: "uuid-123"}, {actionType: 1, metadata: 1})
```

Should show:
```javascript
{
  "actionType": "quote_tweet",
  "metadata": {
    "text": "Your comment",
    "quoted": true
  }
}
```

## Summary

✅ **Quote tweet support added to `/api/v1/reply_by_id` endpoint**
✅ **Optional `quoted` parameter (default: false)**
✅ **Both actions mark tweet as replied in MongoDB**
✅ **Separate action logging (reply vs quote_tweet)**
✅ **Full Postman collection examples**
✅ **Playwright automation for quote tweet flow**

**Key benefit:** One endpoint, two modes of engagement. Choose the right action for your use case!
