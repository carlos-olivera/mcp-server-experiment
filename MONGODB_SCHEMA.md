# MongoDB Schema Design

## Collections

### 1. tweets
Stores all tweets we've interacted with (read, replied to, posted).

```javascript
{
  _id: ObjectId,
  idTweet: String,              // MongoDB-assigned unique ID (UUID)
  tweetId: String,              // Twitter's tweet ID
  text: String,
  authorUsername: String,
  createdAt: ISODate,
  url: String,
  type: String,                 // "mention" | "regular" | "reply" | "posted_by_us"

  // Engagement metrics
  retweetCount: Number,
  likeCount: Number,
  replyCount: Number,

  // Our interaction tracking
  repliedTo: Boolean,           // Have we replied to this?
  repliedAt: ISODate,           // When did we reply?
  replyTweetId: String,         // ID of our reply tweet

  repostedByUs: Boolean,        // Have we retweeted this?
  repostedAt: ISODate,

  ignored: Boolean,             // Marked as ignored (abuse prevention)
  ignoredReason: String,        // Why ignored: "spam" | "duplicate_user" | "blocked_user"
  ignoredAt: ISODate,

  // Metadata
  firstSeenAt: ISODate,         // When we first scraped this
  lastUpdatedAt: ISODate
}
```

**Indexes:**
- `{ tweetId: 1 }` - Unique
- `{ idTweet: 1 }` - Unique
- `{ type: 1, repliedTo: 1, ignored: 1 }` - For filtering unanswered
- `{ authorUsername: 1, createdAt: -1 }` - For user tweet queries
- `{ ignored: 1, firstSeenAt: -1 }` - For abuse tracking

### 2. mentions
Specialized collection for mentions (could merge with tweets but kept separate for clarity).

```javascript
{
  _id: ObjectId,
  idTweet: String,              // MongoDB-assigned unique ID (same as in tweets)
  tweetId: String,              // Twitter's tweet ID
  text: String,
  authorUsername: String,
  authorUserId: String,         // Twitter user ID (if available)
  createdAt: ISODate,
  url: String,

  // Mention-specific
  mentionedUsers: [String],     // [@user1, @user2, ...]

  // Our interaction tracking
  repliedTo: Boolean,
  repliedAt: ISODate,
  replyTweetId: String,

  ignored: Boolean,
  ignoredReason: String,
  ignoredAt: ISODate,

  // Metadata
  firstSeenAt: ISODate,
  lastUpdatedAt: ISODate
}
```

**Indexes:**
- `{ tweetId: 1 }` - Unique
- `{ idTweet: 1 }` - Unique
- `{ repliedTo: 1, ignored: 1, firstSeenAt: -1 }` - Main query pattern
- `{ authorUsername: 1, ignored: 1 }` - Abuse tracking per user

### 3. blocked_users
Tracks users we've blocked due to abuse.

```javascript
{
  _id: ObjectId,
  username: String,             // Twitter username
  userId: String,               // Twitter user ID (if available)

  blockedAt: ISODate,
  blockedReason: String,        // "excessive_mentions" | "spam" | "manual"

  // Statistics
  totalMentions: Number,        // Total mentions from this user
  ignoredMentions: Number,      // How many we ignored

  // Metadata
  firstSeenAt: ISODate,
  lastActivityAt: ISODate
}
```

**Indexes:**
- `{ username: 1 }` - Unique
- `{ blockedAt: -1 }` - For recent blocks

### 4. actions
Audit log of all actions we've taken.

```javascript
{
  _id: ObjectId,
  actionType: String,           // "reply" | "repost" | "post" | "ignore" | "block"

  // Related entities
  targetTweetId: String,        // Tweet we acted on (if applicable)
  targetIdTweet: String,        // Our internal ID
  targetUsername: String,       // User involved

  // Action details
  resultTweetId: String,        // ID of tweet we created (for reply/post)
  reason: String,               // Why we took this action

  success: Boolean,
  errorMessage: String,

  // Metadata
  performedAt: ISODate,
  metadata: Object              // Additional context
}
```

**Indexes:**
- `{ actionType: 1, performedAt: -1 }` - For action history
- `{ targetTweetId: 1 }` - Find actions on specific tweets

## Query Patterns

### Get Unanswered Mentions (with abuse prevention)
```javascript
// 1. Get blocked users
const blockedUsers = await db.blocked_users.distinct('username');

// 2. Query mentions
const mentions = await db.mentions.find({
  repliedTo: false,
  ignored: false,
  authorUsername: { $nin: blockedUsers }
})
.sort({ firstSeenAt: -1 })
.limit(N + buffer);  // Get extra to filter duplicates

// 3. Apply duplicate user filter (in application code)
// If 2+ mentions from same user, keep 1, ignore rest
```

### Get Unanswered Tweets from User
```javascript
const tweets = await db.tweets.find({
  authorUsername: targetUser,
  type: 'regular',
  repliedTo: false,
  ignored: false
})
.sort({ createdAt: -1 })
.limit(N);
```

### Check if User is Blocked
```javascript
const isBlocked = await db.blocked_users.findOne({
  username: username
});
```

### Count Ignored Mentions for User
```javascript
const ignoredCount = await db.mentions.countDocuments({
  authorUsername: username,
  ignored: true
});

// If count >= 10, block user
if (ignoredCount >= 10) {
  await db.blocked_users.insertOne({
    username: username,
    blockedAt: new Date(),
    blockedReason: 'excessive_mentions',
    ignoredMentions: ignoredCount
  });
}
```

## Considerations

### Unified vs Separate Collections
- **Current design**: Separate `mentions` and `tweets` collections
- **Alternative**: Single `tweets` collection with `type` field
- **Decision**: Keep separate for now - easier to query, but can merge if needed

### ID Strategy
- `idTweet`: UUID generated by our application (e.g., `uuid.uuid4()`)
- Stored in both MongoDB and returned in API responses
- Allows clients to reference tweets without exposing Twitter IDs

### Deduplication
- Use `tweetId` (Twitter's ID) as unique constraint
- Before inserting, check if tweet already exists
- Update `lastUpdatedAt` if re-encountered

### Performance
- Index on common query patterns
- Consider TTL index for old ignored mentions (cleanup)
- Consider aggregation pipeline for complex abuse detection
