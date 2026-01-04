#!/usr/bin/env python3
"""
Example AI Agent using Headlock Mode.

This demonstrates how an AI agent can use the headlock system to pause
and wait for user instructions between tasks.
"""

import sys
import time

# Add parent to path for imports
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from src.client import HeadlockClient


def execute_task(instruction: str) -> str:
    """
    Simulate executing a task based on user instruction.
    In a real AI agent, this would invoke the AI's capabilities.
    """
    print(f"\n🤖 Executing: {instruction}")
    
    # Simulate work
    time.sleep(1)
    
    # Generate a mock result
    if "list" in instruction.lower():
        result = "Found 5 items:\n- Item 1\n- Item 2\n- Item 3\n- Item 4\n- Item 5"
    elif "search" in instruction.lower():
        result = f"Search completed. Found 3 results matching your query."
    elif "create" in instruction.lower():
        result = "Created successfully!"
    elif "delete" in instruction.lower():
        result = "Deleted successfully!"
    else:
        result = f"Completed task: {instruction}"
    
    print(f"✅ Result: {result}")
    return result


def main():
    """Main agent loop demonstrating headlock mode."""
    server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"
    
    print("=" * 60)
    print("🔒 Headlock Mode AI Agent Example")
    print("=" * 60)
    print(f"Connecting to server: {server_url}")
    print()
    
    client = HeadlockClient(server_url=server_url)
    
    try:
        # Enter headlock mode - this blocks until user sends instruction
        print("📡 Entering headlock mode... waiting for user instruction")
        print("   (Use the terminal client to send instructions)")
        print()
        
        response = client.enter_headlock(
            context="AI Agent ready and waiting for instructions."
        )
        
        print(f"📋 Session ID: {response.session_id}")
        
        # Main loop - process instructions until tap-out
        while not response.should_terminate:
            if response.instruction:
                # Execute the user's instruction
                result = execute_task(response.instruction)
                
                # Continue in headlock mode with the result
                print("\n⏳ Waiting for next instruction...")
                response = client.continue_headlock(
                    session_id=response.session_id,
                    context=f"Last result: {result}"
                )
            else:
                # No instruction (shouldn't happen normally)
                print("⚠️ No instruction received, waiting...")
                response = client.continue_headlock(
                    session_id=response.session_id,
                    context="Still waiting for instructions..."
                )
        
        print("\n" + "=" * 60)
        print("👋 User tapped out - session ended gracefully")
        print("=" * 60)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Agent interrupted by Ctrl+C")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
