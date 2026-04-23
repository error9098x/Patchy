#!/usr/bin/env python3
"""
Test NVIDIA AI Endpoints connection
Usage: export NVIDIA_API_KEY=your_key && python3 test_nvidia.py
"""

import os
import sys

# Get API key from environment
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")

if not NVIDIA_API_KEY:
    print("❌ NVIDIA_API_KEY not set!")
    print("Set it with: export NVIDIA_API_KEY=your_key_here")
    sys.exit(1)

os.environ["NVIDIA_API_KEY"] = NVIDIA_API_KEY

# Import after setting env var
from tools.nvidia_client import chat, test_connection

print("🧪 Testing NVIDIA AI Endpoints (minimax-m2.7)")
print("=" * 50)
print()

# Test 1: Connection
print("Test 1: Connection test...")
if test_connection():
    print("✅ Connection successful!")
else:
    print("❌ Connection failed!")
    sys.exit(1)

print()

# Test 2: Simple chat
print("Test 2: Simple chat (non-streaming)...")
response = chat(
    messages=[
        {"role": "user", "content": "Say hello in one sentence."}
    ],
    max_tokens=50
)
print(f"Response: {response}")
print("✅ Non-streaming works!")
print()

# Test 3: Streaming
print("Test 3: Streaming chat...")
print("Response: ", end="", flush=True)
for chunk in chat(
    messages=[
        {"role": "user", "content": "Count from 1 to 5, separated by commas."}
    ],
    stream=True,
    max_tokens=100
):
    print(chunk, end="", flush=True)
print()
print("✅ Streaming works!")
print()

print("=" * 50)
print("🎉 All tests passed!")
print()
print("NVIDIA AI Endpoints is ready to use!")
print(f"Model: minimaxai/minimax-m2.7")
print(f"Max tokens: 8192")
