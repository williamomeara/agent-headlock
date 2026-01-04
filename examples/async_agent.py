#!/usr/bin/env python3
"""
Async Example AI Agent using Headlock Mode.

This demonstrates an async AI agent using the headlock system.
"""

import asyncio
import sys

# Add parent to path for imports
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from src.client import AsyncHeadlockClient


async def execute_task(instruction: str) -> str:
    """Simulate executing a task asynchronously."""
    print(f"\n🤖 Executing: {instruction}")
    
    # Simulate async work
    await asyncio.sleep(1)
    
    result = f"Completed: {instruction}"
    print(f"✅ Result: {result}")
    return result


async def main():
    """Main async agent loop."""
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
    
    print("🔒 Async Headlock Mode AI Agent")
    print(f"Connecting to: {server_url}\n")
    
    client = AsyncHeadlockClient(server_url=server_url)
    
    try:
        print("📡 Entering headlock mode...")
        response = await client.enter_headlock(
            context="Async AI Agent ready."
        )
        
        print(f"📋 Session: {response.session_id[:8]}...")
        
        while not response.should_terminate:
            if response.instruction:
                result = await execute_task(response.instruction)
                print("\n⏳ Waiting for next instruction...")
                response = await client.continue_headlock(
                    session_id=response.session_id,
                    context=result
                )
        
        print("\n👋 Session ended by tap-out")
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
