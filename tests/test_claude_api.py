#!/usr/bin/env python3
"""
Test script for Claude API integration
Simple test to verify curl command works with Claude API
"""

import json
import subprocess
import os
import sys
from dotenv import load_dotenv


def test_claude_api():
    """Test the Claude API call."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("No CLAUDE_API_KEY found in .env file or environment variables.")
        api_key = input("Enter your Claude API key: ").strip()
        if not api_key:
            print("No API key provided. Exiting.")
            return False
    
    # Test message
    test_message = "Hello Claude! This is a test message. Please respond with a simple greeting."
    
    # Prepare the API request
    api_request = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": test_message}
        ]
    }
    
    print("Testing Claude API with curl...")
    print(f"Test message: {test_message}")
    print("-" * 50)
    
    try:
        # Make the API call using curl
        curl_command = [
            "curl", "-s", "-X", "POST", "https://api.anthropic.com/v1/messages",
            "-H", f"x-api-key: {api_key}",
            "-H", "content-type: application/json",
            "-H", "anthropic-version: 2023-06-01",
            "-d", json.dumps(api_request)
        ]
        
        print("Executing curl command...")
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=30)
        
        print(f"Curl return code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        
        # Parse the response
        print("Parsing response...")
        response_data = json.loads(result.stdout)
        
        print("API Response:")
        print(json.dumps(response_data, indent=2))
        
        if "content" in response_data and len(response_data["content"]) > 0:
            claude_response = response_data["content"][0]["text"]
            print(f"\nClaude's response: {claude_response}")
            print("\nAPI test successful!")
            return True
        else:
            print(f"Unexpected API response format")
            return False
            
    except subprocess.TimeoutExpired:
        print("API call timed out")
        return False
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response from API: {e}")
        print(f"Raw response: {result.stdout}")
        return False
    except Exception as e:
        print(f"Error calling Claude API: {str(e)}")
        return False


if __name__ == "__main__":
    print("Claude API Test")
    print("=" * 30)
    
    success = test_claude_api()
    
    if success:
        print("\nAPI test passed! You can now use claude_cli_real.py")
    else:
        print("\nAPI test failed. Please check your API key and internet connection.")
        print("Make sure you have a valid Claude API key from: https://console.anthropic.com/")
