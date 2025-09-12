#!/bin/bash

echo "Claude API Setup Script"
echo "======================="
echo ""

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo "Error: curl is not installed. Please install curl first."
    exit 1
fi

echo "curl is available"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "python3 is available"

# Check for existing API key
if [ -n "$CLAUDE_API_KEY" ]; then
    echo "CLAUDE_API_KEY environment variable is set"
    echo "Current API key: ${CLAUDE_API_KEY:0:10}..."
else
    echo "CLAUDE_API_KEY environment variable is not set"
    echo ""
    echo "To set your API key, you can:"
    echo "1. Export it for this session:"
    echo "   export CLAUDE_API_KEY='your-api-key-here'"
    echo ""
    echo "2. Add it to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo "   echo 'export CLAUDE_API_KEY=\"your-api-key-here\"' >> ~/.bashrc"
    echo ""
    echo "3. Get your API key from: https://console.anthropic.com/"
    echo ""
    
    read -p "Would you like to set the API key now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your Claude API key: " api_key
        export CLAUDE_API_KEY="$api_key"
        echo "API key set for this session"
    fi
fi

echo ""
echo "Testing Claude API integration..."
echo ""

# Run the test script
python3 test_claude_api.py

echo ""
echo "Setup complete!"
echo ""
echo "To use the real Claude CLI with blockchain hashing:"
echo "  python3 claude_cli_real.py"
echo ""
echo "To use the simulated version (no API key needed):"
echo "  python3 claude_cli.py"
echo ""
echo "To run the demo:"
echo "  python3 demo_claude_cli.py"
