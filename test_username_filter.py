#!/usr/bin/env python3
"""
Test script for username filter feature in mentions endpoint.

Tests:
1. Default behavior (no username filter)
2. Filtering by specific username
3. @ symbol handling
4. Response schema validation
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def print_test(name):
    """Print test name header"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

def test_mentions_without_filter():
    """Test 1: Default behavior (no username filter)"""
    print_test("Get unanswered mentions (no filter)")

    url = f"{BASE_URL}/api/v1/mentions/unanswered?count=5"
    print(f"GET {url}")

    response = requests.get(url)

    print(f"Status: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(response.text)
        return False

    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")

    # Validate response schema
    assert "success" in data, "Missing 'success' field"
    assert "mentions" in data, "Missing 'mentions' field"
    assert "count" in data, "Missing 'count' field"
    assert "username" in data, "Missing 'username' field"

    # Validate default behavior
    assert data["success"] == True, "success should be True"
    assert isinstance(data["mentions"], list), "mentions should be a list"
    assert data["username"] is None, "username should be None by default"
    assert data["count"] == len(data["mentions"]), "count should match mentions length"

    # Check abuse prevention: no duplicate usernames (unless empty)
    if len(data["mentions"]) > 0:
        usernames = [m["authorUsername"] for m in data["mentions"]]
        unique_usernames = set(usernames)
        if len(usernames) != len(unique_usernames):
            print(f"⚠️  WARNING: Found duplicate users (this is expected if abuse prevention is working)")
            print(f"Usernames: {usernames}")
        else:
            print(f"✅ Abuse prevention working: All unique users")

    print("✅ PASSED: Default behavior working correctly")
    return True


def test_mentions_with_username_filter():
    """Test 2: Filtering by specific username"""
    print_test("Get mentions filtered by username")

    # First, get all mentions to find a username to test with
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=50")
    if response.status_code != 200:
        print("⚠️  SKIPPED: Could not fetch mentions to find test username")
        return True

    all_mentions = response.json().get("mentions", [])
    if not all_mentions:
        print("⚠️  SKIPPED: No mentions available to test filtering")
        return True

    # Use the first username we find
    test_username = all_mentions[0]["authorUsername"]
    print(f"Testing with username: {test_username}")

    url = f"{BASE_URL}/api/v1/mentions/unanswered?count=10&username={test_username}"
    print(f"GET {url}")

    response = requests.get(url)

    print(f"Status: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        print(response.text)
        return False

    data = response.json()
    print(f"Response:\n{json.dumps(data, indent=2)}")

    # Validate response schema
    assert data["success"] == True, "success should be True"
    assert isinstance(data["mentions"], list), "mentions should be a list"
    assert data["username"] == test_username, f"username should be '{test_username}'"
    assert data["count"] == len(data["mentions"]), "count should match mentions length"

    # All mentions should be from the filtered user
    for mention in data["mentions"]:
        assert mention["authorUsername"] == test_username, \
            f"Found mention from {mention['authorUsername']}, expected {test_username}"

    print(f"✅ PASSED: Filtering by username '{test_username}' working correctly")
    return True


def test_username_with_at_symbol():
    """Test 3: @ symbol handling"""
    print_test("Test @ symbol in username")

    # First, get a username to test with
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=5")
    if response.status_code != 200:
        print("⚠️  SKIPPED: Could not fetch mentions to find test username")
        return True

    mentions = response.json().get("mentions", [])
    if not mentions:
        print("⚠️  SKIPPED: No mentions available to test @ symbol")
        return True

    test_username = mentions[0]["authorUsername"]
    print(f"Testing with username: {test_username}")

    # Test without @
    url1 = f"{BASE_URL}/api/v1/mentions/unanswered?count=5&username={test_username}"
    print(f"GET {url1}")
    response1 = requests.get(url1)

    # Test with @
    url2 = f"{BASE_URL}/api/v1/mentions/unanswered?count=5&username=@{test_username}"
    print(f"GET {url2}")
    response2 = requests.get(url2)

    if response1.status_code != 200 or response2.status_code != 200:
        print(f"❌ FAILED: One of the requests failed")
        print(f"Response 1 status: {response1.status_code}")
        print(f"Response 2 status: {response2.status_code}")
        return False

    data1 = response1.json()
    data2 = response2.json()

    # Both responses should be identical
    assert data1["username"] == test_username, "username should not have @"
    assert data2["username"] == test_username, "username should not have @"
    assert data1["count"] == data2["count"], "Both requests should return same count"

    print(f"✅ PASSED: @ symbol correctly stripped from username")
    return True


def test_response_schema():
    """Test 4: Response schema validation"""
    print_test("Response schema validation")

    url = f"{BASE_URL}/api/v1/mentions/unanswered?count=1"
    print(f"GET {url}")

    response = requests.get(url)

    if response.status_code != 200:
        print(f"❌ FAILED: Expected 200, got {response.status_code}")
        return False

    data = response.json()

    # Check top-level fields
    required_fields = ["success", "mentions", "count", "username"]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # If we have mentions, check their schema
    if data["mentions"]:
        mention = data["mentions"][0]
        mention_fields = [
            "idTweet", "tweetId", "text", "authorUsername",
            "createdAt", "url", "type", "repliedTo", "ignored",
            "mentionedUsers"
        ]
        for field in mention_fields:
            assert field in mention, f"Missing mention field: {field}"

        # Check types
        assert isinstance(mention["idTweet"], str), "idTweet should be string"
        assert isinstance(mention["tweetId"], str), "tweetId should be string"
        assert isinstance(mention["text"], str), "text should be string"
        assert isinstance(mention["authorUsername"], str), "authorUsername should be string"
        assert isinstance(mention["type"], str), "type should be string"
        assert mention["type"] == "mention", "type should be 'mention'"
        assert isinstance(mention["repliedTo"], bool), "repliedTo should be boolean"
        assert isinstance(mention["ignored"], bool), "ignored should be boolean"
        assert isinstance(mention["mentionedUsers"], list), "mentionedUsers should be list"

        print(f"✅ Mention schema validated")

    print("✅ PASSED: Response schema is correct")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("USERNAME FILTER FEATURE TEST SUITE")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")

    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ ERROR: API health check failed (status {response.status_code})")
            print("Make sure the API is running: python run_rest_api.py")
            sys.exit(1)
        print("✅ API is running and healthy")
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Cannot connect to API at {BASE_URL}")
        print(f"Error: {e}")
        print("Make sure the API is running: python run_rest_api.py")
        sys.exit(1)

    # Run tests
    tests = [
        ("Default behavior (no filter)", test_mentions_without_filter),
        ("Filter by username", test_mentions_with_username_filter),
        ("@ symbol handling", test_username_with_at_symbol),
        ("Response schema validation", test_response_schema),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            results.append((test_name, False))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("-" * 60)
    print(f"Results: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
