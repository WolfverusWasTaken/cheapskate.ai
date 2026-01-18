"""
MODULE 6: Main Entry Point (Dev 1)
Purpose: Orchestrator that wires everything together

Features:
- Launches visible Chromium browser
- Awaits CLI prompts
- Routes commands through Controller Agent
- Handles graceful shutdown
"""

import asyncio
import sys
from pathlib import Path

from browser_loader import BrowserLoader
from controller import ControllerAgent
from llm_factory import LLMFactory
from config import config
from bridge_server import BridgeServer


# ASCII Art Banner
BANNER = r"""
╔═══════════════════════════════════════════════════════════════════╗
║   ██████╗ █████╗ ██████╗  ██████╗ ██╗   ██╗███████╗███████╗██╗    ║
║  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██║   ██║██╔════╝██╔════╝██║    ║
║  ██║     ███████║██████╔╝██║   ██║██║   ██║███████╗█████╗  ██║    ║
║  ██║     ██╔══██║██╔══██╗██║   ██║██║   ██║╚════██║██╔══╝  ██║    ║
║  ╚██████╗██║  ██║██║  ██║╚██████╔╝╚██████╔╝███████║███████╗███████╗║
║   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚══════╝║
║                                                                   ║
║              🔥 LOWBALLER AGENT 🔥                                 ║
║         Carousell Negotiation Automation                         ║
╚═══════════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Commands:
  find <query>          - Search for items (e.g., "find iPhone 14 under $3000")
  listings              - Show current extracted listings
  open <index>          - Open a specific listing
  chat <index>          - Open chat with seller
  lowball <index>       - Start negotiation on a listing
  voice                 - Record voice message, transcribe, and send to chat
  check_chat            - Go to inbox and stay updated
  screenshot            - Take a screenshot
  history               - Show negotiation history
  help                  - Show this help
  quit / exit           - Exit the agent
  
Examples:
  >>> find people selling iPhone 14 under $3000
  >>> listings
  >>> lowball 0
  >>> chat 1
  >>> voice
"""


async def main():
    """Main entry point for the Carousell Lowballer Agent."""
    
    print(BANNER)
    print(f"LLM Provider: {config.llm.provider}")
    print(f"Model: {config.get_litellm_model()}")
    print(f"Headless: {config.agent.headless_browser}")
    print("-" * 60)
    
    # Create directories
    Path("screenshots").mkdir(exist_ok=True)
    
    # Initialize browser
    browser = BrowserLoader(headless=config.agent.headless_browser)
    
    try:
        print("\n🚀 Launching browser...")
        await browser.launch()
        
        # Navigate to Carousell
        print("🌐 Navigating to Carousell.sg...")
        await browser.navigate("https://www.carousell.sg")
        await asyncio.sleep(2)
        
        # Auto-login if credentials provided and not already logged in
        if config.agent.username and config.agent.password:
            if not await browser.is_logged_in():
                print("🔑 Auto-login triggered...")
                await browser.login(config.agent.username, config.agent.password)
            else:
                print("✅ Already logged in (session restored)")
        
        # Initialize LLM and Controller
        print("🤖 Initializing LLM and Controller...")
        llm = LLMFactory.from_env()
        controller = ControllerAgent(llm, browser)
        
        # Initialize Bridge for Tauri dashboard
        bridge = BridgeServer(port=5001)
        asyncio.create_task(bridge.start())
        
        print("\n✅ Agent ready! Type 'help' for commands.\n")
        print(HELP_TEXT)
        bridge.add_log("SYSTEM", "Agent started and connected to browser.")

        async def get_stdin_input():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, sys.stdin.readline)

        # Main loop
        while True:
            try:
                # Check if background stream detected a new message
                if browser.pending_chat_action:
                    browser.pending_chat_action = False  # Clear flag
                    print("\n🤖 [AUTO] Processing new message from inbox...")
                    bridge.add_log("AGENT", "Auto-detected new message, processing...")
                    result = await controller.run("go to the inbox and stay updated")
                    print(f"\n{result}")
                    bridge.add_log("AGENT", result)
                    continue

                # Wait for input from either Terminal (stdin) or Bridge (Tauri)
                bridge_cmd_task = asyncio.create_task(bridge.command_queue.get())
                stdin_task = asyncio.create_task(get_stdin_input())
                
                # Use timeout to periodically check pending_chat_action
                done, pending = await asyncio.wait(
                    [bridge_cmd_task, stdin_task],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=2.0  # Short timeout to check for auto-actions
                )
                
                # Cleanup pending tasks
                for task in pending:
                    task.cancel()
                
                # If timeout, loop back to check pending_chat_action
                if not done:
                    continue
                
                # Determine source
                if bridge_cmd_task in done:
                    prompt = bridge_cmd_task.result().strip()
                    print(f"\n[DASHBOARD] >>> {prompt}")
                    bridge.add_log("USER", prompt)
                else:
                    prompt = stdin_task.result().strip()
                
                if not prompt:
                    continue
                
                # Handle special commands
                lower_prompt = prompt.lower()
                
                if lower_prompt in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if lower_prompt == 'help':
                    print(HELP_TEXT)
                    continue
                
                if lower_prompt == 'history':
                    if controller.lowballer:
                        print(controller.lowballer.get_chat_summary())
                    else:
                        print("No negotiation history yet.")
                    continue
                
                if lower_prompt == 'listings':
                    prompt = "extract and show current listings"
                
                if lower_prompt.startswith('open '):
                    try:
                        idx = int(prompt.split()[1])
                        prompt = f"open listing {idx}"
                    except (IndexError, ValueError):
                        print("Usage: open <listing_index>")
                        continue
                
                if lower_prompt.startswith('chat '):
                    try:
                        idx = int(prompt.split()[1])
                        prompt = f"open chat for listing {idx}"
                    except (IndexError, ValueError):
                        print("Usage: chat <listing_index>")
                        continue
                
                if lower_prompt.startswith('lowball '):
                    try:
                        idx = int(prompt.split()[1])
                        prompt = f"delegate lowball negotiation for listing {idx}"
                    except (IndexError, ValueError):
                        print("Usage: lowball <listing_index>")
                        continue
                
                if lower_prompt == 'screenshot':
                    prompt = "take a screenshot of the current page"
                
                if lower_prompt == 'voice':
                    prompt = "record voice message and send to chat"
                
                if lower_prompt == 'check_chat' or lower_prompt == 'inbox':
                    prompt = "go to the inbox and stay updated"
                
                # Process through controller
                print(f"\n🤖 Processing...")
                bridge.add_log("AGENT", "Processing command...")
                
                result = await controller.run(prompt)
                
                print(f"\n{result}")
                bridge.add_log("AGENT", result)
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted. Type 'quit' to exit or continue...")
                continue
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await browser.close()
        print("✅ Browser closed.")


def run():
    """Synchronous entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Agent terminated.")
        sys.exit(0)


if __name__ == "__main__":
    run()
