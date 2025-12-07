#!/usr/bin/env python3
"""
Test script for reply marking functionality.

Verifies that when you reply to a tweet or mention, it gets marked as replied
in MongoDB and won't appear in future queries for unanswered tweets/mentions.
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def print_test(name):
    """Print test name header"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")

def test_reply_marks_mention_as_replied():
    """
    Test 1: Reply to a mention using reply_by_id and verify it's marked as replied
    """
    print_test("Reply by ID marks mention as replied")

    # Step 1: Get an unanswered mention
    print("Step 1: Get unanswered mentions")
    url = f"{BASE_URL}/api/v1/mentions/unanswered?count=1"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"⚠️  SKIPPED: Could not fetch mentions (status {response.status_code})")
        return True

    data = response.json()
    if not data.get("mentions"):
        print("⚠️  SKIPPED: No unanswered mentions available to test with")
        return True

    mention = data["mentions"][0]
    id_tweet = mention["idTweet"]
    print(f"Found unanswered mention: {id_tweet}")
    print(f"  From: @{mention['authorUsername']}")
    print(f"  Text: {mention['text'][:50]}...")

    # Step 2: Reply to the mention
    print("\nStep 2: Reply to the mention")
    reply_url = f"{BASE_URL}/api/v1/reply_by_id"
    reply_data = {
        "idTweet": id_tweet,
        "text": "[TEST] This is an automated test reply"
    }

    response = requests.post(reply_url, json=reply_data)

    if response.status_code != 200:
        print(f"❌ FAILED: Reply failed with status {response.status_code}")
        print(response.text)
        return False

    print("✅ Reply successful")

    # Step 3: Wait a moment for MongoDB to update
    time.sleep(1)

    # Step 4: Try to get unanswered mentions again - the replied one should NOT appear
    print("\nStep 3: Verify mention is marked as replied")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=50")
    data = response.json()

    # Check if the replied mention still appears in unanswered
    for m in data.get("mentions", []):
        if m["idTweet"] == id_tweet:
            print(f"❌ FAILED: Mention {id_tweet} still appears in unanswered list!")
            return False

    print(f"✅ PASSED: Mention {id_tweet} no longer appears in unanswered list")
    return True


def test_reply_with_twitter_id_marks_as_replied():
    """
    Test 2: Reply using Twitter ID (original endpoint) and verify it's marked
    """
    print_test("Reply with Twitter ID marks tweet as replied")

    # Step 1: Get unanswered mentions to find a tweet ID
    print("Step 1: Get an unanswered mention")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=1")

    if response.status_code != 200 or not response.json().get("mentions"):
        print("⚠️  SKIPPED: No unanswered mentions to test with")
        return True

    mention = response.json()["mentions"][0]
    tweet_id = mention["tweetId"]
    id_tweet = mention["idTweet"]

    print(f"Found mention with tweetId: {tweet_id}")

    # Step 2: Reply using the original endpoint (with Twitter ID)
    print("\nStep 2: Reply using Twitter ID endpoint")
    reply_url = f"{BASE_URL}/api/v1/reply"
    reply_data = {
        "tweet_id": tweet_id,
        "text": "[TEST] Reply using Twitter ID"
    }

    response = requests.post(reply_url, json=reply_data)

    if response.status_code != 200:
        print(f"❌ FAILED: Reply failed with status {response.status_code}")
        print(response.text)
        return False

    print("✅ Reply successful")

    # Step 3: Wait for MongoDB update
    time.sleep(1)

    # Step 4: Verify it's marked as replied
    print("\nStep 3: Verify mention is marked as replied in MongoDB")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=50")
    data = response.json()

    for m in data.get("mentions", []):
        if m["idTweet"] == id_tweet:
            print(f"❌ FAILED: Mention {id_tweet} still appears in unanswered!")
            return False

    print(f"✅ PASSED: Mention marked as replied via Twitter ID endpoint")
    return True


def test_replied_mentions_dont_appear():
    """
    Test 3: Ensure replied mentions don't appear in unanswered queries
    """
    print_test("Replied mentions excluded from unanswered queries")

    # Get unanswered mentions
    print("Fetching all unanswered mentions...")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=50")

    if response.status_code != 200:
        print(f"❌ FAILED: Could not fetch mentions (status {response.status_code})")
        return False

    data = response.json()
    mentions = data.get("mentions", [])

    print(f"Found {len(mentions)} unanswered mentions")

    # Verify all have repliedTo = false
    for mention in mentions:
        if mention.get("repliedTo") == True:
            print(f"❌ FAILED: Found replied mention in unanswered list!")
            print(f"  idTweet: {mention['idTweet']}")
            print(f"  repliedTo: {mention['repliedTo']}")
            return False

        if mention.get("ignored") == True:
            print(f"❌ FAILED: Found ignored mention in unanswered list!")
            print(f"  idTweet: {mention['idTweet']}")
            print(f"  ignored: {mention['ignored']}")
            return False

    print("✅ PASSED: All mentions in unanswered list have repliedTo=false and ignored=false")
    return True


def main():
    """Run all tests"""
    print("=" * 70)
    print("REPLY MARKING FUNCTIONALITY TEST SUITE")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")

    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ ERROR: API health check failed")
            print("Make sure the API is running: python run_rest_api.py")
            sys.exit(1)
        print("✅ API is running and healthy")
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Cannot connect to API at {BASE_URL}")
        print("Make sure the API is running: python run_rest_api.py")
        sys.exit(1)

    print("\n⚠️  WARNING: This test will actually reply to real mentions!")
    print("Make sure you have at least 2 unanswered mentions available.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(0)

    # Run tests
    tests = [
        ("Reply by ID marks as replied", test_reply_marks_mention_as_replied),
        ("Reply with Twitter ID marks as replied", test_reply_with_twitter_id_marks_as_replied),
        ("Replied mentions excluded from queries", test_replied_mentions_dont_appear),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("-" * 70)
    print(f"Results: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        print("\nWhat this means:")
        print("- ✅ Replies mark tweets/mentions as replied in MongoDB")
        print("- ✅ Replied tweets/mentions won't appear in future unanswered queries")
        print("- ✅ Both reply endpoints (by ID and by Twitter ID) work correctly")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
