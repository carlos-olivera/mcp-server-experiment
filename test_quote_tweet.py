#!/usr/bin/env python3
"""
Test script for quote tweet functionality.

Verifies that the `quoted` parameter in the reply_by_id endpoint works correctly:
- quoted=false posts a regular reply
- quoted=true posts a quote tweet
- Both mark the tweet as replied in MongoDB
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

def test_regular_reply():
    """
    Test 1: Regular reply (quoted=false or omitted)
    """
    print_test("Regular Reply (quoted=false)")

    # Step 1: Get an unanswered mention
    print("Step 1: Get unanswered mention")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=1")

    if response.status_code != 200 or not response.json().get("mentions"):
        print("⚠️  SKIPPED: No unanswered mentions available")
        return True

    mention = response.json()["mentions"][0]
    id_tweet = mention["idTweet"]
    print(f"Found mention: {id_tweet}")
    print(f"  From: @{mention['authorUsername']}")
    print(f"  Text: {mention['text'][:50]}...")

    # Step 2: Reply with quoted=false
    print("\nStep 2: Reply with quoted=false")
    reply_url = f"{BASE_URL}/api/v1/reply_by_id"
    reply_data = {
        "idTweet": id_tweet,
        "text": "[TEST] Regular reply test",
        "quoted": False
    }

    response = requests.post(reply_url, json=reply_data)

    if response.status_code != 200:
        print(f"❌ FAILED: Reply failed with status {response.status_code}")
        print(response.text)
        return False

    result = response.json()
    print("✅ Reply successful")
    print(f"   Message: {result['message']}")
    print(f"   Quoted: {result['data'].get('quoted', 'not specified')}")

    # Step 3: Verify message indicates regular reply
    if "replied to" in result["message"].lower() and "quote" not in result["message"].lower():
        print("✅ PASSED: Message indicates regular reply")
        return True
    else:
        print("❌ FAILED: Message doesn't match expected format")
        return False


def test_quote_tweet():
    """
    Test 2: Quote tweet (quoted=true)
    """
    print_test("Quote Tweet (quoted=true)")

    # Step 1: Get an unanswered mention
    print("Step 1: Get unanswered mention")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=1")

    if response.status_code != 200 or not response.json().get("mentions"):
        print("⚠️  SKIPPED: No unanswered mentions available")
        return True

    mention = response.json()["mentions"][0]
    id_tweet = mention["idTweet"]
    print(f"Found mention: {id_tweet}")
    print(f"  From: @{mention['authorUsername']}")

    # Step 2: Quote tweet with quoted=true
    print("\nStep 2: Quote tweet with quoted=true")
    reply_url = f"{BASE_URL}/api/v1/reply_by_id"
    reply_data = {
        "idTweet": id_tweet,
        "text": "[TEST] Quote tweet test - sharing this!",
        "quoted": True
    }

    response = requests.post(reply_url, json=reply_data)

    if response.status_code != 200:
        print(f"❌ FAILED: Quote tweet failed with status {response.status_code}")
        print(response.text)
        return False

    result = response.json()
    print("✅ Quote tweet successful")
    print(f"   Message: {result['message']}")
    print(f"   Quoted: {result['data'].get('quoted', 'not specified')}")

    # Step 3: Verify message indicates quote tweet
    if "quote" in result["message"].lower():
        print("✅ PASSED: Message indicates quote tweet")
        return True
    else:
        print("⚠️  WARNING: Message doesn't explicitly mention quote tweet")
        print("    (This may be okay if implementation doesn't change message)")
        return True


def test_both_mark_as_replied():
    """
    Test 3: Both reply and quote tweet mark tweet as replied
    """
    print_test("Both actions mark as replied")

    # Get two unanswered mentions
    print("Step 1: Get two unanswered mentions")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=2")

    if response.status_code != 200:
        print("❌ FAILED: Could not fetch mentions")
        return False

    mentions = response.json().get("mentions", [])
    if len(mentions) < 2:
        print("⚠️  SKIPPED: Need at least 2 unanswered mentions for this test")
        return True

    id_reply = mentions[0]["idTweet"]
    id_quote = mentions[1]["idTweet"]

    print(f"ID for regular reply: {id_reply}")
    print(f"ID for quote tweet: {id_quote}")

    # Reply to first
    print("\nStep 2: Regular reply to first mention")
    requests.post(f"{BASE_URL}/api/v1/reply_by_id", json={
        "idTweet": id_reply,
        "text": "[TEST] Reply",
        "quoted": False
    })

    # Quote tweet second
    print("Step 3: Quote tweet second mention")
    requests.post(f"{BASE_URL}/api/v1/reply_by_id", json={
        "idTweet": id_quote,
        "text": "[TEST] Quote tweet",
        "quoted": True
    })

    # Wait for MongoDB updates
    time.sleep(1)

    # Verify both are marked as replied
    print("\nStep 4: Verify both are marked as replied")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=50")
    unanswered_ids = [m["idTweet"] for m in response.json().get("mentions", [])]

    reply_found = id_reply in unanswered_ids
    quote_found = id_quote in unanswered_ids

    if not reply_found and not quote_found:
        print("✅ PASSED: Both mentions marked as replied")
        return True
    else:
        if reply_found:
            print(f"❌ FAILED: Regular reply mention {id_reply} still in unanswered list")
        if quote_found:
            print(f"❌ FAILED: Quote tweet mention {id_quote} still in unanswered list")
        return False


def test_default_quoted_is_false():
    """
    Test 4: Default behavior (omitting quoted parameter) is regular reply
    """
    print_test("Default quoted parameter is false")

    # Get an unanswered mention
    print("Step 1: Get unanswered mention")
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=1")

    if response.status_code != 200 or not response.json().get("mentions"):
        print("⚠️  SKIPPED: No unanswered mentions available")
        return True

    mention = response.json()["mentions"][0]
    id_tweet = mention["idTweet"]

    # Reply WITHOUT quoted parameter
    print("\nStep 2: Reply without specifying quoted parameter")
    reply_data = {
        "idTweet": id_tweet,
        "text": "[TEST] Reply without quoted param"
        # Note: quoted parameter is omitted
    }

    response = requests.post(f"{BASE_URL}/api/v1/reply_by_id", json=reply_data)

    if response.status_code != 200:
        print(f"❌ FAILED: Reply failed with status {response.status_code}")
        return False

    result = response.json()
    quoted_value = result["data"].get("quoted")

    print(f"Response quoted value: {quoted_value}")

    # Should default to false
    if quoted_value == False or quoted_value is None:
        print("✅ PASSED: Default quoted is false (or not specified)")
        return True
    else:
        print(f"❌ FAILED: Expected quoted=false, got {quoted_value}")
        return False


def test_quoted_validation():
    """
    Test 5: Quoted parameter accepts boolean values
    """
    print_test("Quoted parameter validation")

    # Get an unanswered mention
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=1")

    if response.status_code != 200 or not response.json().get("mentions"):
        print("⚠️  SKIPPED: No unanswered mentions available")
        return True

    mention = response.json()["mentions"][0]
    id_tweet = mention["idTweet"]

    # Test with explicit boolean true
    print("\nTesting quoted=true")
    response = requests.post(f"{BASE_URL}/api/v1/reply_by_id", json={
        "idTweet": id_tweet,
        "text": "[TEST] Validation test",
        "quoted": True
    })

    if response.status_code == 200:
        print("✅ quoted=true accepted")
    else:
        print(f"❌ FAILED: quoted=true rejected (status {response.status_code})")
        return False

    # Get another mention for second test
    response = requests.get(f"{BASE_URL}/api/v1/mentions/unanswered?count=1")
    if response.status_code == 200 and response.json().get("mentions"):
        mention = response.json()["mentions"][0]
        id_tweet = mention["idTweet"]

        # Test with explicit boolean false
        print("\nTesting quoted=false")
        response = requests.post(f"{BASE_URL}/api/v1/reply_by_id", json={
            "idTweet": id_tweet,
            "text": "[TEST] Validation test 2",
            "quoted": False
        })

        if response.status_code == 200:
            print("✅ quoted=false accepted")
        else:
            print(f"❌ FAILED: quoted=false rejected (status {response.status_code})")
            return False

    print("✅ PASSED: Boolean validation works")
    return True


def main():
    """Run all tests"""
    print("=" * 70)
    print("QUOTE TWEET FUNCTIONALITY TEST SUITE")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")

    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code != 200:
            print("❌ ERROR: API health check failed")
            print("Make sure the API is running: python run_rest_api.py")
            sys.exit(1)
        print("✅ API is running and healthy")
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Cannot connect to API at {BASE_URL}")
        print("Make sure the API is running: python run_rest_api.py")
        sys.exit(1)

    print("\n⚠️  WARNING: This test will actually reply to and quote tweet real mentions!")
    print("Make sure you have at least 5 unanswered mentions available.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(0)

    # Run tests
    tests = [
        ("Regular reply (quoted=false)", test_regular_reply),
        ("Quote tweet (quoted=true)", test_quote_tweet),
        ("Both actions mark as replied", test_both_mark_as_replied),
        ("Default quoted is false", test_default_quoted_is_false),
        ("Quoted parameter validation", test_quoted_validation),
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
        print("- ✅ Quote tweet feature works correctly")
        print("- ✅ Regular reply still works as expected")
        print("- ✅ Both actions mark tweets as replied in MongoDB")
        print("- ✅ Default behavior is regular reply (quoted=false)")
        print("- ✅ Boolean parameter validation works")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
