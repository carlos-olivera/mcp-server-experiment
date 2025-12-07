// MongoDB Index Creation Script
// Run this script as a database administrator with proper permissions
//
// Usage:
//   mongo mongodb://adminUser:adminPass@192.168.50.139:27017/xserver?authSource=admin create_mongodb_indexes.js
//
// Or connect to mongo shell and run:
//   use xserver
//   load('create_mongodb_indexes.js')

// Switch to the xserver database
db = db.getSiblingDB('xserver');

print('Creating indexes for Twitter MCP Agent...\n');

// ============================================
// TWEETS COLLECTION INDEXES
// ============================================
print('Creating indexes for tweets collection...');

try {
    db.tweets.createIndex({ "tweetId": 1 }, { unique: true });
    print('✓ Created unique index on tweets.tweetId');
} catch (e) {
    print('✗ Error creating index on tweets.tweetId: ' + e.message);
}

try {
    db.tweets.createIndex({ "idTweet": 1 }, { unique: true });
    print('✓ Created unique index on tweets.idTweet');
} catch (e) {
    print('✗ Error creating index on tweets.idTweet: ' + e.message);
}

try {
    db.tweets.createIndex({ "type": 1, "repliedTo": 1, "ignored": 1 });
    print('✓ Created compound index on tweets.type + repliedTo + ignored');
} catch (e) {
    print('✗ Error creating compound index: ' + e.message);
}

try {
    db.tweets.createIndex({ "authorUsername": 1, "createdAt": -1 });
    print('✓ Created compound index on tweets.authorUsername + createdAt');
} catch (e) {
    print('✗ Error creating compound index: ' + e.message);
}

try {
    db.tweets.createIndex({ "ignored": 1, "firstSeenAt": -1 });
    print('✓ Created compound index on tweets.ignored + firstSeenAt');
} catch (e) {
    print('✗ Error creating compound index: ' + e.message);
}

// ============================================
// MENTIONS COLLECTION INDEXES
// ============================================
print('\nCreating indexes for mentions collection...');

try {
    db.mentions.createIndex({ "tweetId": 1 }, { unique: true });
    print('✓ Created unique index on mentions.tweetId');
} catch (e) {
    print('✗ Error creating index on mentions.tweetId: ' + e.message);
}

try {
    db.mentions.createIndex({ "idTweet": 1 }, { unique: true });
    print('✓ Created unique index on mentions.idTweet');
} catch (e) {
    print('✗ Error creating index on mentions.idTweet: ' + e.message);
}

try {
    db.mentions.createIndex({ "repliedTo": 1, "ignored": 1, "firstSeenAt": -1 });
    print('✓ Created compound index on mentions.repliedTo + ignored + firstSeenAt');
} catch (e) {
    print('✗ Error creating compound index: ' + e.message);
}

try {
    db.mentions.createIndex({ "authorUsername": 1, "ignored": 1 });
    print('✓ Created compound index on mentions.authorUsername + ignored');
} catch (e) {
    print('✗ Error creating compound index: ' + e.message);
}

// ============================================
// BLOCKED_USERS COLLECTION INDEXES
// ============================================
print('\nCreating indexes for blocked_users collection...');

try {
    db.blocked_users.createIndex({ "username": 1 }, { unique: true });
    print('✓ Created unique index on blocked_users.username');
} catch (e) {
    print('✗ Error creating index on blocked_users.username: ' + e.message);
}

try {
    db.blocked_users.createIndex({ "blockedAt": -1 });
    print('✓ Created index on blocked_users.blockedAt');
} catch (e) {
    print('✗ Error creating index: ' + e.message);
}

// ============================================
// ACTIONS COLLECTION INDEXES
// ============================================
print('\nCreating indexes for actions collection...');

try {
    db.actions.createIndex({ "actionType": 1, "performedAt": -1 });
    print('✓ Created compound index on actions.actionType + performedAt');
} catch (e) {
    print('✗ Error creating compound index: ' + e.message);
}

try {
    db.actions.createIndex({ "targetTweetId": 1 });
    print('✓ Created index on actions.targetTweetId');
} catch (e) {
    print('✗ Error creating index: ' + e.message);
}

// ============================================
// SUMMARY
// ============================================
print('\n========================================');
print('Index creation complete!');
print('========================================\n');

print('Verifying indexes...\n');

print('tweets collection indexes:');
printjson(db.tweets.getIndexes());

print('\nmentions collection indexes:');
printjson(db.mentions.getIndexes());

print('\nblocked_users collection indexes:');
printjson(db.blocked_users.getIndexes());

print('\nactions collection indexes:');
printjson(db.actions.getIndexes());

print('\n✅ All indexes created successfully!');
print('\nNote: The application will work without indexes, but performance may be degraded.');
print('These indexes are recommended for production use.');
