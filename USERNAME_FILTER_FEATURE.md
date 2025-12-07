# Username Filter Feature for Mentions Endpoint

## Overview

The `/api/v1/mentions/unanswered` endpoint now supports an optional `username` query parameter that filters mentions to show only those from a specific user.

## What's New

### Before
```bash
# Could only get all unanswered mentions (max 1 per user due to abuse prevention)
GET /api/v1/mentions/unanswered?count=5
```

### After
```bash
# Get all unanswered mentions (existing behavior)
GET /api/v1/mentions/unanswered?count=5

# NEW: Get all unanswered mentions from specific user
GET /api/v1/mentions/unanswered?count=10&username=alice123
```

## Use Cases

### Use Case 1: Priority User Monitoring
Monitor mentions from VIP users or important accounts:

```bash
# Check all mentions from your CEO
curl "http://localhost:8000/api/v1/mentions/unanswered?username=ceo_account"

# Check mentions from support team
curl "http://localhost:8000/api/v1/mentions/unanswered?username=support_team&count=20"
```

### Use Case 2: Targeted Response Campaigns
Respond to all mentions from a specific user:

```bash
# Get all unanswered mentions from influencer
MENTIONS=$(curl -s "http://localhost:8000/api/v1/mentions/unanswered?username=influencer_name&count=50")

# Reply to each one
for id in $(echo $MENTIONS | jq -r '.mentions[].idTweet'); do
  curl -X POST "http://localhost:8000/api/v1/reply_by_id" \
    -H "Content-Type: application/json" \
    -d "{
      \"idTweet\": \"$id\",
      \"text\": \"Thanks for your continued support!\"
    }"
done
```

### Use Case 3: Customer Service Workflows
Handle all pending questions from a specific customer:

```bash
# Get all mentions from customer
curl "http://localhost:8000/api/v1/mentions/unanswered?username=customer_johndoe&count=100"
```

## API Specification

### Endpoint
```
GET /api/v1/mentions/unanswered
```

### Query Parameters

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `count` | integer | No | 5 | 1-50 | Number of mentions to return |
| `username` | string | No | null | - | Twitter username (with or without @) |

### Response Schema

```typescript
{
  success: boolean,
  mentions: Array<{
    idTweet: string,          // MongoDB UUID
    tweetId: string,          // Twitter's tweet ID
    text: string,
    authorUsername: string,
    createdAt: string,        // ISO 8601 timestamp
    url: string,
    type: "mention",
    repliedTo: boolean,
    ignored: boolean,
    mentionedUsers: string[]
  }>,
  count: number,
  username: string | null     // Set when filtering by username
}
```

## Implementation Details

### Code Changes

#### 1. MongoRepository ([src/infrastructure/mongo_repository.py](src/infrastructure/mongo_repository.py:322-404))

**Added `username` parameter:**
```python
async def get_unanswered_mentions(
    self,
    limit: int = 5,
    apply_abuse_filter: bool = True,
    username: Optional[str] = None  # NEW
) -> List[Mention]:
```

**Query building logic:**
```python
# Build query
query = {
    "repliedTo": False,
    "ignored": False,
    "authorUsername": {"$nin": blocked_usernames}
}

# Add username filter if specified
if username:
    if username in blocked_usernames:
        logger.warning(f"Requested user @{username} is blocked")
        return []
    query["authorUsername"] = username  # Override to match specific user
```

**Abuse filter behavior:**
```python
# If filtering by specific username, skip abuse filter (all from same user)
if username or not apply_abuse_filter:
    return all_mentions[:limit]
```

#### 2. GetUnansweredMentionsUseCase ([src/domain/use_cases_extended.py](src/domain/use_cases_extended.py:33-93))

**Added `username` parameter:**
```python
async def execute(self, count: int = 5, username: str = None) -> List[Mention]:
    if username:
        logger.info(f"Getting {count} unanswered mentions from @{username}")
    # ...
    mentions = await self.mongo_repo.get_unanswered_mentions(
        limit=count,
        apply_abuse_filter=True,
        username=username
    )
```

#### 3. API Route ([src/api/routes.py](src/api/routes.py:302-343))

**Added query parameter:**
```python
@router.get("/mentions/unanswered", response_model=UnansweredMentionsResponse)
async def get_unanswered_mentions(
    count: int = Query(5, ge=1, le=50),
    username: str = Query(None, description="Optional: filter mentions from specific user")
):
    if username:
        username = username.lstrip('@')

    mentions = await _get_unanswered_mentions_use_case.execute(count, username)
```

#### 4. Response Schema ([src/api/schemas.py](src/api/schemas.py:99-109))

**Added `username` field:**
```python
class UnansweredMentionsResponse(BaseModel):
    success: bool
    mentions: List[Dict[str, Any]]
    count: int
    username: Optional[str] = None  # NEW: Set when filtering by specific user
```

## Behavior Details

### Abuse Prevention

**Without username filter (default):**
- Returns max 1 mention per user per batch
- Marks duplicate mentions from same user as ignored
- Auto-blocks users with 10+ ignored mentions
- Excludes blocked users

**With username filter:**
- Returns ALL mentions from specified user (up to `count`)
- Skips duplicate user filtering (all mentions are from same user)
- Still excludes blocked users (returns empty if user is blocked)
- Does NOT mark anything as ignored

### Blocked Users

If the requested username is blocked:
```bash
curl "http://localhost:8000/api/v1/mentions/unanswered?username=blocked_user"
```

**Response:**
```json
{
  "success": true,
  "mentions": [],
  "count": 0,
  "username": "blocked_user"
}
```

**Log output:**
```
WARNING - Requested user @blocked_user is blocked, returning empty list
```

## Examples

### Example 1: Get All Unanswered Mentions

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
      "text": "@mybot Help!",
      "authorUsername": "user1",
      "createdAt": "2024-12-07T10:00:00",
      "url": "https://x.com/user1/status/1234567890",
      "type": "mention",
      "repliedTo": false,
      "ignored": false,
      "mentionedUsers": ["@mybot"]
    },
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440001",
      "tweetId": "1234567891",
      "text": "@mybot Question?",
      "authorUsername": "user2",
      "createdAt": "2024-12-07T09:30:00",
      "url": "https://x.com/user2/status/1234567891",
      "type": "mention",
      "repliedTo": false,
      "ignored": false,
      "mentionedUsers": ["@mybot"]
    }
  ],
  "count": 2,
  "username": null
}
```

### Example 2: Get Mentions from Specific User

**Request:**
```bash
curl "http://localhost:8000/api/v1/mentions/unanswered?count=10&username=alice123"
```

**Response:**
```json
{
  "success": true,
  "mentions": [
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440010",
      "tweetId": "1234567899",
      "text": "@mybot I need help with my account",
      "authorUsername": "alice123",
      "createdAt": "2024-12-07T11:00:00",
      "url": "https://x.com/alice123/status/1234567899",
      "type": "mention",
      "repliedTo": false,
      "ignored": false,
      "mentionedUsers": ["@mybot"]
    },
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440011",
      "tweetId": "1234567900",
      "text": "@mybot Still waiting for response",
      "authorUsername": "alice123",
      "createdAt": "2024-12-07T10:45:00",
      "url": "https://x.com/alice123/status/1234567900",
      "type": "mention",
      "repliedTo": false,
      "ignored": false,
      "mentionedUsers": ["@mybot"]
    },
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440012",
      "tweetId": "1234567901",
      "text": "@mybot Are you there?",
      "authorUsername": "alice123",
      "createdAt": "2024-12-07T10:30:00",
      "url": "https://x.com/alice123/status/1234567901",
      "type": "mention",
      "repliedTo": false,
      "ignored": false,
      "mentionedUsers": ["@mybot"]
    }
  ],
  "count": 3,
  "username": "alice123"
}
```

Note: All 3 mentions are from the same user (no duplicate filtering applied).

### Example 3: Username with @ Symbol

The API automatically strips the `@` symbol:

```bash
# These are equivalent:
curl "http://localhost:8000/api/v1/mentions/unanswered?username=alice123"
curl "http://localhost:8000/api/v1/mentions/unanswered?username=@alice123"
```

## Testing

### Manual Testing

1. **Test without username (default behavior):**
   ```bash
   curl "http://localhost:8000/api/v1/mentions/unanswered?count=5" | jq '.'
   ```
   ✓ Should return max 1 mention per user
   ✓ `username` field should be `null`

2. **Test with username:**
   ```bash
   curl "http://localhost:8000/api/v1/mentions/unanswered?count=10&username=testuser" | jq '.'
   ```
   ✓ Should return all mentions from `testuser` (up to 10)
   ✓ `username` field should be `"testuser"`
   ✓ All mentions should have `authorUsername: "testuser"`

3. **Test with blocked user:**
   ```bash
   # First, block a user by having 10+ ignored mentions
   # Then try to get mentions from that user
   curl "http://localhost:8000/api/v1/mentions/unanswered?username=blocked_user" | jq '.'
   ```
   ✓ Should return empty array
   ✓ Log should show warning about blocked user

4. **Test with @ symbol:**
   ```bash
   curl "http://localhost:8000/api/v1/mentions/unanswered?username=@testuser" | jq '.'
   ```
   ✓ Should work the same as without @
   ✓ Response `username` field should be `"testuser"` (without @)

### Integration Testing

```python
import requests

BASE_URL = "http://localhost:8000"

def test_mentions_without_filter():
    """Test default behavior (no username filter)"""
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=5")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["username"] is None

    # Check abuse prevention: no duplicate usernames
    usernames = [m["authorUsername"] for m in data["mentions"]]
    assert len(usernames) == len(set(usernames)), "Duplicate users found!"

def test_mentions_with_username_filter():
    """Test filtering by specific username"""
    test_username = "alice123"
    response = requests.get(
        f"{BASE_URL}/api/v1/mentions/unanswered",
        params={"count": 10, "username": test_username}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["username"] == test_username

    # All mentions should be from the filtered user
    for mention in data["mentions"]:
        assert mention["authorUsername"] == test_username

def test_username_with_at_symbol():
    """Test that @ symbol is stripped"""
    response1 = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?username=alice")
    response2 = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?username=@alice")

    assert response1.json() == response2.json()

if __name__ == "__main__":
    test_mentions_without_filter()
    test_mentions_with_username_filter()
    test_username_with_at_symbol()
    print("✅ All tests passed!")
```

## Postman Collection

The feature is included in the [Twitter_MCP_Agent.postman_collection.json](Twitter_MCP_Agent.postman_collection.json):

**Request: "Get Unanswered Mentions"**
- Default example: `?count=5`
- With username parameter (disabled by default, enable to test)

**Response: "Filtered by Username"**
- Shows example response when filtering by `alice123`
- Includes `username` field in response

## MongoDB Queries

### Get mentions from specific user in MongoDB

```javascript
// Connect to MongoDB
mongo mongodb://criptoUser:criptoPass456@192.168.50.139:27017/xserver?authSource=admin

use xserver

// Find all unanswered mentions from specific user
db.mentions.find({
  "authorUsername": "alice123",
  "repliedTo": false,
  "ignored": false
}).sort({"firstSeenAt": -1})

// Count unanswered mentions per user
db.mentions.aggregate([
  {
    $match: {
      "repliedTo": false,
      "ignored": false
    }
  },
  {
    $group: {
      _id: "$authorUsername",
      count: { $sum: 1 }
    }
  },
  {
    $sort: { count: -1 }
  }
])
```

## Performance Considerations

### Without Username Filter
- Fetches `limit * 3` mentions from MongoDB (buffer for filtering)
- Applies abuse prevention algorithm (O(n) iteration)
- Returns up to `limit` mentions

### With Username Filter
- Fetches exactly `limit` mentions from MongoDB
- Skips abuse prevention algorithm
- Returns up to `limit` mentions
- **More efficient** when you know the username

### MongoDB Indexes

The `authorUsername` field is indexed for fast filtering:
```javascript
db.mentions.createIndex({ "authorUsername": 1, "ignored": 1 })
```

## Backward Compatibility

✅ **Fully backward compatible**

- Existing API calls without `username` parameter work exactly as before
- Response schema is extended (added optional `username` field)
- No breaking changes to existing behavior

## Related Documentation

- [QUICK_START.md](QUICK_START.md) - Updated with username filter examples
- [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Feature summary
- [Twitter_MCP_Agent.postman_collection.json](Twitter_MCP_Agent.postman_collection.json) - API collection with examples

## Support

For issues or questions about this feature:
1. Check logs for warnings about blocked users
2. Verify MongoDB has mentions from the requested username
3. Test with Postman collection
4. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
