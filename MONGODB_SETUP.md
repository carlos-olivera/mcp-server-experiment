# MongoDB Setup Guide

This guide helps you set up MongoDB for the Twitter MCP Agent.

## Prerequisites

- MongoDB server running and accessible
- Database administrator credentials (for initial setup)
- Network access to MongoDB server

## Current Configuration

According to your `.env` file:

```env
MONGO_USER=criptoUser
MONGO_PASSWORD=criptoPass456
MONGO_HOST=192.168.50.139
MONGO_PORT=27017
MONGO_DB=xserver
MONGO_AUTH_SOURCE=admin
```

## Step 1: Verify MongoDB Connection

First, verify that you can connect to MongoDB:

```bash
# Test basic connectivity
ping 192.168.50.139

# Test MongoDB port
nc -zv 192.168.50.139 27017

# Or using telnet
telnet 192.168.50.139 27017
```

## Step 2: Verify User Credentials

Connect to MongoDB using the mongo shell to verify credentials:

```bash
mongo mongodb://criptoUser:criptoPass456@192.168.50.139:27017/xserver?authSource=admin
```

### If Connection Fails

**Error: "Authentication failed"**

This means:
- The username `criptoUser` doesn't exist
- The password is incorrect
- The user exists but in a different auth database

**Solutions:**

1. **Check if user exists:**
   ```javascript
   // Connect as admin
   mongo mongodb://adminUser:adminPass@192.168.50.139:27017/admin

   // Check users
   use admin
   db.getUsers()
   ```

2. **Create the user if it doesn't exist:**
   ```javascript
   // As database administrator
   use admin
   db.createUser({
     user: "criptoUser",
     pwd: "criptoPass456",
     roles: [
       { role: "readWrite", db: "xserver" },
       { role: "dbAdmin", db: "xserver" }  // Optional: for index creation
     ]
   })
   ```

3. **Update the password if needed:**
   ```javascript
   // As database administrator
   use admin
   db.changeUserPassword("criptoUser", "criptoPass456")
   ```

## Step 3: Grant Required Permissions

The application needs these permissions:

### Minimum Permissions (Read/Write)

```javascript
// As database administrator
use admin
db.grantRolesToUser("criptoUser", [
  { role: "readWrite", db: "xserver" }
])
```

With only `readWrite`, the application will:
- ✅ Work correctly for all operations
- ⚠️ Show warning about index creation
- ⚠️ May have slower performance without indexes

### Recommended Permissions (Read/Write + Index Management)

```javascript
// As database administrator
use admin
db.grantRolesToUser("criptoUser", [
  { role: "readWrite", db: "xserver" },
  { role: "dbAdmin", db: "xserver" }
])
```

With `dbAdmin`, the application will:
- ✅ Automatically create all indexes
- ✅ Optimal query performance
- ✅ No warnings on startup

### Full Permissions (Owner - Development Only)

```javascript
// As database administrator
use admin
db.grantRolesToUser("criptoUser", [
  { role: "dbOwner", db: "xserver" }
])
```

⚠️ **Warning:** Only use `dbOwner` in development. In production, use minimal permissions.

## Step 4: Create Indexes (If User Lacks Permissions)

If `criptoUser` doesn't have `dbAdmin` role, a database administrator must create indexes:

```bash
# Download the index creation script
# Then run as admin
mongo mongodb://adminUser:adminPass@192.168.50.139:27017/xserver?authSource=admin create_mongodb_indexes.js
```

Or manually in mongo shell:

```javascript
use xserver

// Tweets collection
db.tweets.createIndex({ "tweetId": 1 }, { unique: true })
db.tweets.createIndex({ "idTweet": 1 }, { unique: true })
db.tweets.createIndex({ "type": 1, "repliedTo": 1, "ignored": 1 })
db.tweets.createIndex({ "authorUsername": 1, "createdAt": -1 })
db.tweets.createIndex({ "ignored": 1, "firstSeenAt": -1 })

// Mentions collection
db.mentions.createIndex({ "tweetId": 1 }, { unique: true })
db.mentions.createIndex({ "idTweet": 1 }, { unique: true })
db.mentions.createIndex({ "repliedTo": 1, "ignored": 1, "firstSeenAt": -1 })
db.mentions.createIndex({ "authorUsername": 1, "ignored": 1 })

// Blocked users collection
db.blocked_users.createIndex({ "username": 1 }, { unique: true })
db.blocked_users.createIndex({ "blockedAt": -1 })

// Actions collection
db.actions.createIndex({ "actionType": 1, "performedAt": -1 })
db.actions.createIndex({ "targetTweetId": 1 })
```

## Step 5: Verify Setup

Test the complete setup:

```bash
# 1. Connect and verify permissions
mongo mongodb://criptoUser:criptoPass456@192.168.50.139:27017/xserver?authSource=admin

# 2. In mongo shell:
use xserver

# Test write permission
db.tweets.insertOne({test: true})

# Test read permission
db.tweets.find({test: true})

# Cleanup test
db.tweets.deleteOne({test: true})

# Check indexes
db.tweets.getIndexes()
db.mentions.getIndexes()
```

## Step 6: Update .env File

If you needed to change credentials, update your `.env` file:

```env
MONGO_USER=yourActualUsername
MONGO_PASSWORD=yourActualPassword
MONGO_HOST=192.168.50.139
MONGO_PORT=27017
MONGO_DB=xserver
MONGO_AUTH_SOURCE=admin
```

## Step 7: Start the Application

```bash
python run_rest_api.py
```

### Expected Output (Success)

```
INFO - Starting Twitter MCP Agent REST API
INFO - Initializing MongoDB connection
INFO - Initializing MongoDB indexes
INFO - MongoDB indexes created successfully
INFO - MongoDB connected to 192.168.50.139:27017/xserver
INFO - Browser manager started
INFO - REST API startup complete
```

### Expected Output (Success without index permissions)

```
INFO - Starting Twitter MCP Agent REST API
INFO - Initializing MongoDB connection
INFO - Initializing MongoDB indexes
WARNING - MongoDB user lacks permission to create indexes
INFO - MongoDB connected to 192.168.50.139:27017/xserver
INFO - Browser manager started
INFO - REST API startup complete
```

## Common Issues

### Issue: "Network timeout"

**Cause:** Cannot reach MongoDB server

**Solutions:**
1. Check firewall: `sudo ufw allow 27017`
2. Check MongoDB is listening: `netstat -an | grep 27017`
3. Check MongoDB bind IP in mongod.conf: `bindIp: 0.0.0.0`

### Issue: "Authentication failed"

**Cause:** Wrong username, password, or auth database

**Solutions:**
1. Verify credentials with mongo shell
2. Check auth source matches user creation database
3. Recreate user if necessary

### Issue: "Not authorized"

**Cause:** User lacks required permissions

**Solutions:**
1. Grant `readWrite` role minimum
2. Grant `dbAdmin` role for index creation
3. Have admin create indexes manually

### Issue: "Connection refused"

**Cause:** MongoDB not running or wrong port

**Solutions:**
1. Start MongoDB: `sudo systemctl start mongod`
2. Verify port: `sudo netstat -tulpn | grep mongo`
3. Check mongod.conf for correct port

## Security Best Practices

### Production Environment

1. **Use strong passwords:**
   ```bash
   # Generate secure password
   openssl rand -base64 32
   ```

2. **Limit permissions:**
   - Application user: `readWrite` only
   - Admin creates indexes separately
   - Don't grant `dbOwner` to application users

3. **Enable TLS:**
   ```env
   # Use TLS connection
   MONGO_URI=mongodb://user:pass@host:27017/db?tls=true
   ```

4. **Network security:**
   - Firewall rules restricting MongoDB port
   - VPN or private network only
   - IP whitelisting if possible

5. **Audit logging:**
   Enable MongoDB audit logs to track access

### Development Environment

For development, you can use more permissive settings:

```javascript
// Create dev user with full access
use admin
db.createUser({
  user: "devUser",
  pwd: "devPassword",
  roles: [
    { role: "dbOwner", db: "xserver" }
  ]
})
```

## Testing MongoDB Setup

Use this script to test your MongoDB configuration:

```bash
#!/bin/bash
# test_mongodb.sh

echo "Testing MongoDB connection..."

# Source .env file
source .env

# Build connection URI
MONGO_URI="mongodb://${MONGO_USER}:${MONGO_PASSWORD}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}?authSource=${MONGO_AUTH_SOURCE}"

echo "Connection URI: mongodb://${MONGO_USER}:****@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}?authSource=${MONGO_AUTH_SOURCE}"

# Test connection
mongo "$MONGO_URI" --eval "db.runCommand({ ping: 1 })"

if [ $? -eq 0 ]; then
    echo "✅ MongoDB connection successful!"

    # Test write permission
    mongo "$MONGO_URI" --eval "db.test.insertOne({test:true})" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Write permission confirmed"
        mongo "$MONGO_URI" --eval "db.test.deleteOne({test:true})" > /dev/null 2>&1
    else
        echo "❌ No write permission"
    fi

    # Check indexes
    echo "Checking indexes..."
    mongo "$MONGO_URI" --eval "db.tweets.getIndexes().length"
else
    echo "❌ MongoDB connection failed"
    exit 1
fi
```

## Next Steps

Once MongoDB is set up:

1. Start the application: `python run_rest_api.py`
2. Test the API: `curl http://localhost:8000/docs`
3. Monitor MongoDB: Use MongoDB Compass or mongo shell
4. Check logs: Application logs all MongoDB operations

## Support

For MongoDB-specific issues:
- MongoDB Documentation: https://docs.mongodb.com/
- Connection String Format: https://docs.mongodb.com/manual/reference/connection-string/
- User Management: https://docs.mongodb.com/manual/tutorial/manage-users-and-roles/

For application issues:
- See [QUICK_START.md](QUICK_START.md)
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
