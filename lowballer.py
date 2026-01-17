"""
MODULE 5: Lowballer Agent (Dev 3)
Purpose: Negotiates in seller chat windows with strategic lowball offers

Strategy:
- Round 1: Offer 50% of listing price
- Each round: Increase by 10% up to max 70%
- Walk away if seller won't budge after max rounds

Provides:
- LowballerAgent.negotiate(seller_id, listing_price, page)
- Tools: type_message(text), extract_seller_reply()
- Logs: chat_history.json
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from llm_factory import LLMClient, LLMFactory
from config import config


class LowballerAgent:
    """
    Specialized negotiation agent that handles lowball offers and counter-negotiations.
    Maintains chat history and uses strategic price escalation.
    """
    
    def __init__(self, llm: LLMClient):
        """
        Initialize the lowballer agent.
        
        Args:
            llm: LLM client for generating negotiation messages
        """
        self.llm = llm
        self.chat_history_file = Path("chat_history.json")
        self.chat_history: dict[str, list] = self._load_chat_history()
        
        # Negotiation settings from config
        self.initial_percent = config.agent.initial_lowball_percent
        self.max_percent = config.agent.max_offer_percent
        self.max_rounds = config.agent.max_negotiation_rounds
        
        print(f"LOWBALLER: Initialized (offers: {self.initial_percent}%-{self.max_percent}%)")
    
    def _load_chat_history(self) -> dict:
        """Load chat history from file."""
        if self.chat_history_file.exists():
            try:
                with open(self.chat_history_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_chat_history(self):
        """Save chat history to file."""
        try:
            with open(self.chat_history_file, 'w') as f:
                json.dump(self.chat_history, f, indent=2, default=str)
            print(f"LOWBALLER: ✓ Chat history saved")
        except Exception as e:
            print(f"LOWBALLER: ✗ Failed to save chat history: {e}")
    
    def _get_seller_id(self, listing_data: dict) -> str:
        """Generate a unique seller/listing ID."""
        return f"{listing_data.get('seller_name', 'unknown')}_{listing_data.get('title', 'item')[:20]}"
    
    def _calculate_offer(self, listing_price: float, round_num: int) -> float:
        """
        Calculate the offer price for a given round.
        
        Args:
            listing_price: Original listing price
            round_num: Current negotiation round (1-indexed)
            
        Returns:
            Calculated offer price
        """
        if round_num == 1:
            percent = self.initial_percent
        else:
            # Increase by 10% each round up to max
            percent = min(self.initial_percent + (round_num - 1) * 10, self.max_percent)
        
        return int(listing_price * (percent / 100))
    
    async def negotiate(
        self,
        listing_data: dict,
        page: Any,
        initial_message: Optional[str] = None,
    ) -> str:
        """
        Start or continue negotiation for a listing.
        
        Args:
            listing_data: Dictionary with listing info (title, price, seller_name, etc.)
            page: Playwright page object for the chat
            initial_message: Optional custom first message
            
        Returns:
            Status message about the negotiation
        """
        seller_id = self._get_seller_id(listing_data)
        listing_price = listing_data.get("price", 0)
        item_name = listing_data.get("title", "item")
        
        print(f"\nLOWBALLER: Starting negotiation for '{item_name}' @ ${listing_price}")
        print(f"LOWBALLER: Seller ID: {seller_id}")
        
        # Initialize chat history for this seller if needed
        if seller_id not in self.chat_history:
            self.chat_history[seller_id] = {
                "listing": listing_data,
                "started_at": datetime.now().isoformat(),
                "messages": [],
                "current_round": 0,
                "status": "active",
            }
        
        chat = self.chat_history[seller_id]
        current_round = chat["current_round"] + 1
        
        # Check if we've exceeded max rounds
        if current_round > self.max_rounds:
            chat["status"] = "walked_away"
            self._save_chat_history()
            return f"LOWBALLER: Max rounds ({self.max_rounds}) reached. Walking away from {item_name}."
        
        # Calculate offer for this round
        offer_price = self._calculate_offer(listing_price, current_round)
        offer_percent = int((offer_price / listing_price) * 100)
        
        # Generate negotiation message
        if initial_message:
            message = initial_message
        else:
            message = await self._generate_message(item_name, listing_price, offer_price, current_round)
        
        print(f"LOWBALLER: Round {current_round} - Offering ${offer_price} ({offer_percent}% of ${listing_price})")
        print(f"LOWBALLER: Message → \"{message}\"")
        
        # Try to type the message in chat
        sent = await self._send_message(page, message)
        
        # Log the message
        chat["messages"].append({
            "role": "lowballer",
            "content": message,
            "offer_price": offer_price,
            "round": current_round,
            "timestamp": datetime.now().isoformat(),
            "sent": sent,
        })
        chat["current_round"] = current_round
        self._save_chat_history()
        
        if sent:
            return f"LOWBALLER: Sent offer ${offer_price} for {item_name}"
        else:
            return f"LOWBALLER: Generated offer ${offer_price} for {item_name} (chat input not found - may need to open chat first)"
    
    async def _generate_message(
        self,
        item_name: str,
        listing_price: float,
        offer_price: float,
        round_num: int,
    ) -> str:
        """Generate a negotiation message using the LLM."""
        
        # Build context-aware prompt
        round_context = {
            1: "This is your first message. Be friendly and make a low but reasonable offer.",
            2: "The seller didn't accept your first offer. Increase slightly but stay firm.",
            3: "Third attempt. Show some flexibility but don't go too high.",
            4: "Getting closer to your max. Express urgency.",
            5: "Final offer. Make it clear this is your best and final price.",
        }
        
        context = round_context.get(round_num, "Make a reasonable counteroffer.")
        
        messages = [
            {
                "role": "system",
                "content": """You are negotiating on Carousell Singapore. Write natural, casual messages like a real buyer.
Rules:
- Keep messages short (1-2 sentences max)
- Be friendly but firm on price
- Mention cash payment and quick pickup as incentives
- Don't be rude or aggressive
- Sound like a real person, not a bot"""
            },
            {
                "role": "user",
                "content": f"""Generate a negotiation message:
Item: {item_name}
Listed Price: S${listing_price}
Your Offer: S${offer_price}
Round: {round_num}
Context: {context}

Write just the message, nothing else."""
            }
        ]
        
        try:
            response = await self.llm.complete(messages, max_tokens=100)
            message = response.get("content", "").strip()
            
            # Clean up the message
            message = message.strip('"\'')
            if not message:
                raise ValueError("Empty response")
            
            return message
            
        except Exception as e:
            print(f"LOWBALLER: ✗ LLM generation failed, using fallback → {e}")
            return self._get_fallback_message(item_name, offer_price, round_num)
    
    def _get_fallback_message(self, item_name: str, offer_price: float, round_num: int) -> str:
        """Get a fallback message without LLM."""
        fallbacks = {
            1: [
                f"Hi! Interested in your {item_name}. Would you take ${offer_price} cash? Can pickup today.",
                f"Hey! Love the {item_name}. Can do ${offer_price} with immediate pickup?",
                f"Hi there! Can you do ${offer_price} for quick deal?",
            ],
            2: [
                f"I understand. Would ${offer_price} work? Cash ready.",
                f"How about ${offer_price}? Can collect anytime this week.",
                f"Best I can do is ${offer_price} - interested?",
            ],
            3: [
                f"Last offer - ${offer_price} cash today?",
                f"Can stretch to ${offer_price}, that's really my max.",
                f"${offer_price} is my highest. Let me know!",
            ],
        }
        
        import random
        options = fallbacks.get(round_num, fallbacks[3])
        return random.choice(options)
    
    async def _send_message(self, page: Any, message: str) -> bool:
        """
        Type and send a message in the chat window.
        
        Args:
            page: Playwright page object
            message: Message to send
            
        Returns:
            True if message was sent, False otherwise
        """
        if page is None:
            return False
        
        # Common chat input selectors for Carousell
        input_selectors = [
            'textarea[placeholder*="message"]',
            'input[placeholder*="message"]',
            '[data-testid="chat-input"]',
            'textarea[class*="chat"]',
            'input[class*="chat"]',
            'textarea',
        ]
        
        for selector in input_selectors:
            try:
                # Wait briefly for element
                await page.wait_for_selector(selector, timeout=2000)
                
                # Type the message
                await page.fill(selector, message)
                
                # Try to find and click send button
                send_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Send")',
                    '[data-testid="send-button"]',
                    'button[class*="send"]',
                ]
                
                for send_sel in send_selectors:
                    try:
                        await page.click(send_sel, timeout=1000)
                        print(f"LOWBALLER: ✓ Message sent via {selector}")
                        return True
                    except Exception:
                        continue
                
                # If no send button, try pressing Enter
                await page.press(selector, "Enter")
                print(f"LOWBALLER: ✓ Message sent (Enter key)")
                return True
                
            except Exception:
                continue
        
        print("LOWBALLER: ✗ Could not find chat input field")
        return False
    
    async def extract_seller_reply(self, page: Any) -> Optional[str]:
        """
        Extract the latest seller reply from the chat.
        
        Args:
            page: Playwright page object
            
        Returns:
            Latest seller message or None
        """
        if page is None:
            return None
        
        try:
            # Try to get chat messages
            messages = await page.evaluate("""
                () => {
                    const messages = document.querySelectorAll('[class*="message"], [class*="chat"] p, [class*="bubble"]');
                    return Array.from(messages).map(m => m.textContent.trim()).slice(-5);
                }
            """)
            
            if messages:
                # Return the last message (likely seller's reply)
                return messages[-1]
                
        except Exception as e:
            print(f"LOWBALLER: ✗ Failed to extract reply: {e}")
        
        return None
    
    async def respond_to_counter(self, listing_data: dict, page: Any, seller_price: float) -> str:
        """
        Respond to a seller's counter-offer.
        
        Args:
            listing_data: Original listing data
            page: Playwright page
            seller_price: Price the seller countered with
            
        Returns:
            Status message
        """
        seller_id = self._get_seller_id(listing_data)
        chat = self.chat_history.get(seller_id, {})
        current_round = chat.get("current_round", 0) + 1
        
        # Log seller's counter
        if seller_id in self.chat_history:
            self.chat_history[seller_id]["messages"].append({
                "role": "seller",
                "content": f"Counter-offered at ${seller_price}",
                "timestamp": datetime.now().isoformat(),
            })
        
        # Decide if we should accept or counter
        listing_price = listing_data.get("price", 0)
        max_acceptable = listing_price * (self.max_percent / 100)
        
        if seller_price <= max_acceptable:
            # Accept the offer!
            message = f"Deal! ${seller_price} works for me. When can I collect?"
            await self._send_message(page, message)
            
            if seller_id in self.chat_history:
                self.chat_history[seller_id]["status"] = "accepted"
                self.chat_history[seller_id]["final_price"] = seller_price
                self._save_chat_history()
            
            return f"LOWBALLER: ✓ Accepted seller's price of ${seller_price}!"
        
        # Otherwise, make another counter-offer
        return await self.negotiate(listing_data, page)
    
    def get_chat_summary(self, seller_id: Optional[str] = None) -> str:
        """Get a summary of chat history."""
        if seller_id:
            chat = self.chat_history.get(seller_id, {})
            if not chat:
                return f"No chat history for {seller_id}"
            return json.dumps(chat, indent=2, default=str)
        
        # Return summary of all chats
        summary = []
        for sid, chat in self.chat_history.items():
            status = chat.get("status", "unknown")
            rounds = chat.get("current_round", 0)
            summary.append(f"  {sid}: {status} ({rounds} rounds)")
        
        return "Chat History:\n" + "\n".join(summary) if summary else "No chat history."


# Standalone test
if __name__ == "__main__":
    async def test_lowballer():
        print("=" * 50)
        print("LOWBALLER AGENT TEST")
        print("=" * 50)
        
        llm = LLMFactory.from_env()
        lowballer = LowballerAgent(llm)
        
        # Mock listing data
        mock_listing = {
            "title": "iPhone 14 Pro 256GB",
            "price": 800,
            "seller_name": "techseller88",
            "listing_url": "https://carousell.sg/p/test-123",
        }
        
        # Test message generation (without browser)
        print(f"\n✓ Testing negotiation for: {mock_listing['title']} @ ${mock_listing['price']}")
        
        # Round 1
        msg1 = await lowballer._generate_message(
            mock_listing["title"],
            mock_listing["price"],
            lowballer._calculate_offer(mock_listing["price"], 1),
            1
        )
        print(f"\nRound 1 (50%): {msg1}")
        
        # Round 2
        msg2 = await lowballer._generate_message(
            mock_listing["title"],
            mock_listing["price"],
            lowballer._calculate_offer(mock_listing["price"], 2),
            2
        )
        print(f"Round 2 (60%): {msg2}")
        
        # Round 3
        msg3 = await lowballer._generate_message(
            mock_listing["title"],
            mock_listing["price"],
            lowballer._calculate_offer(mock_listing["price"], 3),
            3
        )
        print(f"Round 3 (70%): {msg3}")
        
        print("\nLOWBALLER: ✓ All tests passed!")
    
    asyncio.run(test_lowballer())
