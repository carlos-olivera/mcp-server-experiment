# Implementation Plan - MongoDB Integration & New Features

## Overview

This document outlines the implementation of:
1. MongoDB persistence for all Twitter interactions
2. New endpoints for mentions and unanswered tweets
3. Abuse prevention and user blocking
4. Complete audit trail

## Progress Status

### ✅ Completed

1. **MongoDB Schema Design** ([MONGODB_SCHEMA.md](MONGODB_SCHEMA.md))
   - Collections: tweets, mentions, blocked_users, actions
   - Indexes for optimal query performance
   - Document structures defined

2. **Configuration** ([src/config.py](src/config.py))
   - MongoDB connection settings added
   - Abuse prevention thresholds configured
   - `get_mongo_uri()` method for connection string

3. **Domain Models** ([src/domain/models.py](src/domain/models.py))
   - `StoredTweet` - Tweet with MongoDB tracking
   - `Mention` - Mention-specific extension
   - `BlockedUser` - Blocked user tracking
   - `Action` - Audit log entries
   - Enums: `TweetType`, `IgnoredReason`, `BlockedReason`

4. **MongoDB Repository** ([src/infrastructure/mongo_repository.py](src/infrastructure/mongo_repository.py))
   - Complete CRUD operations for tweets/mentions
   - Abuse prevention logic
   - User blocking functionality
   - Action logging

### 🔄 In Progress

5. **Twitter Repository Extensions**
   - Need to add `read_mentions()` method
   - Extract mentioned users from tweets

6. **Domain Interfaces**
   - Update `ITwitterRepository` with mention methods

7. **Use Cases**
   - `GetUnansweredMentionsUseCase`
   - `GetUnansweredTweetsFromUserUseCase`
   - `ReplyByIdTweetUseCase`
   - Integration with MongoDB repository

8. **API Endpoints**
   - `GET /api/v1/mentions/unanswered`
   - `GET /api/v1/tweets/unanswered/{username}`
   - `POST /api/v1/reply_by_id`
   - Update existing endpoints to use MongoDB

9. **MCP Tools**
   - Update tools to use new use cases
   - Add mention-related tools

### ⏳ Remaining Tasks

10. **Dependencies**
    - Add `motor` (async MongoDB driver)
    - Add `pymongo` (MongoDB tools)

11. **Database Initialization**
    - Auto-create indexes on startup
    - Migration strategy

12. **Integration**
    - Wire MongoDB repository into FastAPI app
    - Update existing endpoints
    - Add lifespan management

13. **Testing**
    - Test MongoDB operations
    - Test abuse prevention
    - Test new endpoints

14. **Documentation**
    - Update README with new features
    - API examples for new endpoints
    - MongoDB setup instructions

## Implementation Steps (Remaining)

###  Step 1: Add Mention Reading to Twitter Repository

```python
# src/infrastructure/twitter_repository.py

async def read_last_mentions(self, count: int) -> List[Tweet]:
    """
    Read the last N mentions of the authenticated account.

    Args:
        count: Number of mentions to retrieve

    Returns:
        List of Tweet objects representing mentions
    """
    # Navigate to notifications/mentions
    # Extract tweets
    # Parse mentioned users
    # Return as Tweet objects
```

### Step 2: Update Domain Interfaces

```python
# src/domain/interfaces.py

class ITwitterRepository(ABC):
    # ... existing methods ...

    @abstractmethod
    async def read_last_mentions(self, count: int) -> List[Tweet]:
        """Read the last N mentions of the authenticated account."""
        pass
```

### Step 3: Create New Use Cases

```python
# src/domain/use_cases.py

class GetUnansweredMentionsUseCase:
    def __init__(
        self,
        twitter_repo: ITwitterRepository,
        mongo_repo: MongoRepository
    ):
        self.twitter_repo = twitter_repo
        self.mongo_repo = mongo_repo

    async def execute(self, count: int = 5) -> List[Mention]:
        """
        Get unanswered mentions with abuse prevention.

        1. Fetch last N mentions from Twitter
        2. Store/update in MongoDB
        3. Get unanswered mentions from MongoDB (with filtering)
        4. Return up to count mentions
        """
        pass
```

### Step 4: Create API Schemas

```python
# src/api/schemas.py

class UnansweredMentionsResponse(BaseModel):
    success: bool
    mentions: List[Dict[str, Any]]
    count: int

class ReplyByIdRequest(BaseModel):
    idTweet: str
    text: str
```

### Step 5: Add New API Endpoints

```python
# src/api/routes.py

@router.get("/mentions/unanswered")
async def get_unanswered_mentions(count: int = 5):
    """Get unanswered mentions with abuse prevention."""
    pass

@router.get("/tweets/unanswered/{username}")
async def get_unanswered_tweets_from_user(username: str, count: int = 5):
    """Get unanswered tweets from a specific user."""
    pass

@router.post("/reply_by_id")
async def reply_by_id_tweet(request: ReplyByIdRequest):
    """Reply to a tweet by its internal MongoDB ID."""
    pass
```

### Step 6: Wire Up Dependencies

```python
# src/api/app.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Existing browser manager initialization

    # NEW: Initialize MongoDB
    mongo_repo = MongoRepository()
    await mongo_repo.initialize()

    # NEW: Pass mongo_repo to use cases

    yield

    # Cleanup
    await mongo_repo.close()
```

## API Contract Examples

### Get Unanswered Mentions

**Request:**
```http
GET /api/v1/mentions/unanswered?count=5
```

**Response:**
```json
{
  "success": true,
  "mentions": [
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440000",
      "tweetId": "1234567890",
      "text": "@mybot Please help with this",
      "authorUsername": "user123",
      "createdAt": "2024-12-06T12:00:00",
      "url": "https://x.com/user123/status/1234567890",
      "mentionedUsers": ["@mybot"],
      "repliedTo": false,
      "ignored": false
    }
  ],
  "count": 1
}
```

### Get Unanswered Tweets from User

**Request:**
```http
GET /api/v1/tweets/unanswered/elonmusk?count=5
```

**Response:**
```json
{
  "success": true,
  "tweets": [
    {
      "idTweet": "550e8400-e29b-41d4-a716-446655440001",
      "tweetId": "1234567891",
      "text": "Tweet content here",
      "authorUsername": "elonmusk",
      "createdAt": "2024-12-06T13:00:00",
      "url": "https://x.com/elonmusk/status/1234567891",
      "repliedTo": false,
      "ignored": false
    }
  ],
  "count": 1
}
```

### Reply by ID

**Request:**
```http
POST /api/v1/reply_by_id
Content-Type: application/json

{
  "idTweet": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Thanks for your message!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully replied to tweet",
  "data": {
    "original_idTweet": "550e8400-e29b-41d4-a716-446655440000",
    "reply_tweet_id": "1234567892",
    "reply_url": "https://x.com/mybot/status/1234567892"
  }
}
```

## Database Flow

### Mention Processing Flow

```
1. GET /mentions/unanswered
   ↓
2. TwitterRepository.read_last_mentions(count=10)  # Get extra for filtering
   ↓
3. For each mention:
   - Create Mention object
   - MongoRepository.store_mention(mention)
   ↓
4. MongoRepository.get_unanswered_mentions(limit=5)
   - Exclude blocked users
   - Apply duplicate user filter
   - Mark extras as ignored
   - Check for users to block
   ↓
5. Return filtered mentions
```

### Reply Processing Flow

```
1. POST /reply_by_id {idTweet, text}
   ↓
2. MongoRepository.get_mention_by_id_tweet(idTweet)
   - Get mention details
   ↓
3. TwitterRepository.reply_to_tweet(tweetId, text)
   - Post reply on Twitter
   ↓
4. MongoRepository.mark_mention_as_replied(idTweet, replyTweetId)
   - Update MongoDB
   ↓
5. MongoRepository.log_action({type: "reply", ...})
   - Audit trail
   ↓
6. Return success response
```

## Abuse Prevention Logic

Implemented in `MongoRepository.get_unanswered_mentions()`:

1. **Fetch mentions** - Get unanswered, non-ignored mentions from non-blocked users
2. **Filter duplicates** - If 2+ mentions from same user:
   - Keep first mention
   - Mark rest as ignored with reason `DUPLICATE_USER`
3. **Check block threshold** - For each ignored user:
   - Count total ignored mentions
   - If count >= 10, add to `blocked_users` collection
4. **Return filtered list** - Up to requested count

## Next Steps

Due to the large scope of changes, I recommend:

1. **Test MongoDB connection** first
2. **Implement one endpoint at a time**:
   - Start with `GET /mentions/unanswered`
   - Then `POST /reply_by_id`
   - Then `GET /tweets/unanswered/{username}`
3. **Add comprehensive logging** at each step
4. **Test abuse prevention** with mock data

Would you like me to:
- A) Continue implementing all remaining components
- B) Focus on one endpoint as a complete example
- C) Create a minimal working version first, then expand

Let me know your preference and I'll proceed accordingly.
