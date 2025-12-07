# Changelog - Username Filter Feature

## Version: 1.1.0
## Date: 2025-12-07
## Feature: Username Filter for Mentions Endpoint

### Summary

Added optional `username` query parameter to `/api/v1/mentions/unanswered` endpoint, allowing users to filter mentions from a specific Twitter user.

### What Changed

#### New Features

1. **Optional Username Filter**
   - Added `username` query parameter to `GET /api/v1/mentions/unanswered`
   - Automatically strips `@` symbol from username
   - Returns all unanswered mentions from specified user (up to `count` limit)
   - Skips abuse prevention filtering when username is specified

2. **Response Enhancement**
   - Added `username` field to response (null when no filter, username when filtered)
   - Response now indicates which filter was applied

### Modified Files

#### 1. [src/infrastructure/mongo_repository.py](src/infrastructure/mongo_repository.py)
**Lines 322-404**

**Changes:**
- Added `username: Optional[str] = None` parameter to `get_unanswered_mentions()`
- Query builder now filters by specific username when provided
- Returns empty list if requested username is blocked (with warning log)
- Skips abuse prevention algorithm when filtering by username
- Adjusted buffer limit based on whether username filter is used

**Code:**
```python
async def get_unanswered_mentions(
    self,
    limit: int = 5,
    apply_abuse_filter: bool = True,
    username: Optional[str] = None  # NEW
) -> List[Mention]:
```

#### 2. [src/domain/use_cases_extended.py](src/domain/use_cases_extended.py)
**Lines 33-93**

**Changes:**
- Added `username: str = None` parameter to `execute()` method
- Passes username parameter to MongoDB repository
- Updated logging to show when filtering by username

**Code:**
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

#### 3. [src/api/routes.py](src/api/routes.py)
**Lines 302-343**

**Changes:**
- Added `username: str = Query(None, ...)` parameter to route handler
- Strips `@` symbol from username if present
- Passes username to use case
- Includes username in response

**Code:**
```python
@router.get("/mentions/unanswered", response_model=UnansweredMentionsResponse)
async def get_unanswered_mentions(
    count: int = Query(5, ge=1, le=50),
    username: str = Query(None, description="Optional: filter mentions from specific user")
):
    if username:
        username = username.lstrip('@')
```

#### 4. [src/api/schemas.py](src/api/schemas.py)
**Lines 99-109**

**Changes:**
- Added `username: Optional[str] = None` field to `UnansweredMentionsResponse`
- Updated docstring to document the filter capability

**Code:**
```python
class UnansweredMentionsResponse(BaseModel):
    """Response schema for unanswered mentions.

    Can be filtered by username using the optional 'username' query parameter.
    When filtering by username, abuse prevention is skipped (all mentions are from same user).
    """
    success: bool
    mentions: List[Dict[str, Any]]
    count: int
    username: Optional[str] = None  # NEW
```

#### 5. [Twitter_MCP_Agent.postman_collection.json](Twitter_MCP_Agent.postman_collection.json)
**Lines 287-403**

**Changes:**
- Added `username` query parameter (disabled by default) to "Get Unanswered Mentions" request
- Added new response example: "Filtered by Username"
- Updated endpoint description with username filter documentation

**New Query Parameter:**
```json
{
  "key": "username",
  "value": "",
  "description": "Optional: filter mentions from specific user (e.g., 'elonmusk')",
  "disabled": true
}
```

#### 6. [QUICK_START.md](QUICK_START.md)
**Lines 64-108**

**Changes:**
- Added example request with username filter
- Added `username` field to response example
- Documented query parameters
- Added new workflow example: "Responding to Mentions from Specific User"

#### 7. [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)
**Lines 32-49**

**Changes:**
- Updated use case description to mention username filtering
- Added query parameter documentation for mentions endpoint
- Updated abuse prevention description

### New Files

#### 1. [USERNAME_FILTER_FEATURE.md](USERNAME_FILTER_FEATURE.md)
Complete feature documentation including:
- Overview and use cases
- API specification
- Implementation details
- Behavior documentation
- Code examples
- Testing instructions
- MongoDB queries
- Performance considerations

#### 2. [test_username_filter.py](test_username_filter.py)
Comprehensive test suite including:
- Test 1: Default behavior (no filter)
- Test 2: Filtering by specific username
- Test 3: @ symbol handling
- Test 4: Response schema validation

**Usage:**
```bash
python test_username_filter.py
```

### API Changes

#### Before
```http
GET /api/v1/mentions/unanswered?count=5
```

#### After
```http
# All mentions (existing behavior)
GET /api/v1/mentions/unanswered?count=5

# Mentions from specific user (NEW)
GET /api/v1/mentions/unanswered?count=10&username=alice123
```

### Response Changes

#### Before
```json
{
  "success": true,
  "mentions": [...],
  "count": 2
}
```

#### After
```json
{
  "success": true,
  "mentions": [...],
  "count": 2,
  "username": null  // NEW: null or username string
}
```

### Behavior Changes

#### Without Username Filter (Existing Behavior)
- ✅ Returns max 1 mention per user per batch
- ✅ Marks duplicate mentions as ignored
- ✅ Auto-blocks users with 10+ ignored mentions
- ✅ Excludes blocked users

#### With Username Filter (New Behavior)
- ✅ Returns ALL mentions from specified user (up to `count`)
- ✅ Skips duplicate user filtering (all from same user)
- ✅ Still excludes blocked users (returns empty if blocked)
- ✅ Does NOT mark anything as ignored
- ✅ More efficient (no abuse prevention overhead)

### Breaking Changes

**None** - Fully backward compatible.

Existing API calls work exactly as before. The `username` parameter is optional and defaults to `None`, maintaining existing behavior.

### Migration Guide

**No migration required.** This is a purely additive change.

If you want to use the new feature:

```python
# Old way (still works)
response = requests.get("http://localhost:8000/api/v1/mentions/unanswered?count=5")

# New way (optional)
response = requests.get(
    "http://localhost:8000/api/v1/mentions/unanswered",
    params={"count": 10, "username": "alice123"}
)
```

### Testing

#### Manual Testing

```bash
# 1. Test default behavior
curl "http://localhost:8000/api/v1/mentions/unanswered?count=5" | jq '.'

# 2. Test with username filter
curl "http://localhost:8000/api/v1/mentions/unanswered?count=10&username=testuser" | jq '.'

# 3. Test @ symbol handling
curl "http://localhost:8000/api/v1/mentions/unanswered?username=@testuser" | jq '.'
```

#### Automated Testing

```bash
# Run test suite
python test_username_filter.py
```

Expected output:
```
✅ PASS - Default behavior (no filter)
✅ PASS - Filter by username
✅ PASS - @ symbol handling
✅ PASS - Response schema validation

Results: 4/4 tests passed

🎉 All tests passed!
```

### Performance Impact

**Positive impact when using username filter:**
- Fetches exactly `limit` mentions (vs `limit * 3` buffer)
- Skips abuse prevention algorithm (O(n) iteration)
- MongoDB query is more specific (indexed field)

**No impact on existing usage:**
- Default behavior unchanged
- Same performance characteristics

### Security Considerations

**No new security concerns:**
- Username parameter is properly sanitized (@ stripped)
- Blocked users still excluded
- No SQL injection risk (using MongoDB parameterized queries)
- No information disclosure (blocked users return empty, not error)

### Documentation Updates

All documentation has been updated:
- ✅ [QUICK_START.md](QUICK_START.md) - Usage examples
- ✅ [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) - Feature summary
- ✅ [Twitter_MCP_Agent.postman_collection.json](Twitter_MCP_Agent.postman_collection.json) - API collection
- ✅ [USERNAME_FILTER_FEATURE.md](USERNAME_FILTER_FEATURE.md) - Complete feature guide

### Known Limitations

1. **Case Sensitivity**: Username matching is case-sensitive
   - `alice123` ≠ `Alice123`
   - Twitter usernames are case-insensitive, but our filter is case-sensitive
   - **Workaround**: Use exact username as stored in database

2. **Blocked Users**: Returns empty array (not an error)
   - May be confusing if user doesn't check logs
   - **Workaround**: Check MongoDB blocked_users collection

3. **No Partial Matching**: Must provide exact username
   - Cannot use wildcards like `alice*`
   - **Workaround**: Query MongoDB directly for partial matches

### Future Enhancements

Potential improvements (not implemented):

1. **Case-Insensitive Filtering**
   ```python
   query["authorUsername"] = {"$regex": f"^{username}$", "$options": "i"}
   ```

2. **Multiple Username Filter**
   ```python
   usernames: List[str] = Query(None)
   query["authorUsername"] = {"$in": usernames}
   ```

3. **Date Range Filter**
   ```python
   since: datetime = Query(None)
   until: datetime = Query(None)
   query["createdAt"] = {"$gte": since, "$lte": until}
   ```

4. **Pagination**
   ```python
   offset: int = Query(0)
   cursor.skip(offset).limit(limit)
   ```

### Support

For questions or issues:
- See [USERNAME_FILTER_FEATURE.md](USERNAME_FILTER_FEATURE.md) for detailed documentation
- Run test suite: `python test_username_filter.py`
- Check logs for warnings about blocked users
- Verify MongoDB data: `db.mentions.find({authorUsername: "user"}).pretty()`

### Contributors

- Feature implemented: 2025-12-07
- Tested: Automated test suite included
- Documented: Complete documentation provided

### References

- Pull Request: N/A (direct commit)
- Issue: N/A (feature request)
- Discussion: N/A
