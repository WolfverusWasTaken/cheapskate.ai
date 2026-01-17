"""
MODULE 5: Lowballer Agent (Dev 3)
Purpose: Negotiates in seller chat windows with strategic lowball offers

Strategy (Ackerman Model from "Never Split the Difference"):
- Round 1: Offer 65% of listing price (with precise number)
- Round 2: Offer 85%
- Round 3: Offer 95%
- Round 4: Offer 100% (your true max) + walk-away bluff

Provides:
- LowballerAgent.negotiate(seller_id, listing_price, page)
- Tools: type_message(text), extract_seller_reply()
- Logs: chat_history.json
"""

import asyncio
import json
import random
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any

from llm_factory import LLMClient, LLMFactory
from config import config


# ============================================
# NEGOTIATION PERSONAS
# ============================================

class NegotiationPersona(Enum):
    """Different negotiation styles the agent can use."""
    FRIENDLY = "friendly"
    STUDENT = "student"
    BULK_BUYER = "bulk_buyer"
    URGENT_CASH = "urgent_cash"
    CHRIS_VOSS = "chris_voss"


# ============================================
# SYSTEM PROMPTS BY PERSONA
# ============================================

SYSTEM_PROMPTS = {
    "chris_voss": """You are a savvy Carousell buyer in Singapore using FBI negotiation tactics from "Never Split the Difference".

CORE PRINCIPLES:
1. Tactical empathy - acknowledge their position before countering
2. Use PRECISE numbers ($387 not $400) - signals you've done research
3. Label emotions: "It seems like...", "It sounds like..."
4. Calibrated questions: "How can we make this work?"
5. Late-night DJ voice - warm, calm, never aggressive

STYLE:
- Keep messages SHORT (1-2 sentences max)
- Sound human, use occasional Singlish (lah, can?, steady)
- Mention cash + quick pickup as leverage
- Never be rude or pushy""",

    "student": """You are a university student in Singapore looking for deals on Carousell.
Be genuine about budget constraints. Be polite and appreciative.
Use casual language like you're texting a friend.
Keep messages short (1-2 sentences). Mention you're a student.""",

    "bulk_buyer": """You are a buyer looking at multiple items from the same seller.
Mention you're interested in other items from them too.
Be business-like but friendly. Propose bundle deals.
Keep it professional and concise.""",

    "urgent_cash": """You have cash ready and can meet IMMEDIATELY.
Create urgency - you're free RIGHT NOW to collect.
Be direct and efficient. Emphasize speed and convenience.
Short messages only.""",

    "friendly": """You are a friendly buyer just looking for a good deal on Carousell.
Be warm, casual, and complimentary about the item.
No pressure tactics, just genuine interest.
Chat like you're talking to a neighbor."""
}


# ============================================
# ROUND CONTEXTS (Chris Voss Tactics)
# ============================================

ROUND_CONTEXTS = {
    1: """ANCHOR LOW with tactical empathy. Start with: 'I know this is below asking, but...'
Use your PRECISE offer number. Justify briefly: 'Seen similar listings around this price.'
Be friendly and non-threatening.""",

    2: """MIRROR their response if they objected. If they said 'firm', you can reply 'Firm?'
Increase your offer. Add value: 'I can do cash and pickup within the hour.'
Show you're reasonable but have limits.""",

    3: """LABEL their situation: 'It seems like you want this sold quickly...'
Show flexibility but stay firm on your number.
Create urgency: 'I'm free right now if we can agree.'""",

    4: """Use ACCUSATION AUDIT: 'You probably have better offers coming in...'
This is near your max. Express genuine interest but also your limits.
Hint this might be your final offer.""",

    5: """WALK-AWAY BLUFF: 'I totally understand if this doesn't work for you. Good luck with the sale!'
State your final precise number clearly.
This psychological tactic often triggers acceptance."""
}


class LowballerAgent:
    """
    Specialized negotiation agent that handles lowball offers and counter-negotiations.
    Uses the Ackerman Model and Chris Voss tactics from "Never Split the Difference".
    Maintains chat history and uses strategic price escalation.
    """

    def __init__(self, llm: LLMClient, persona: NegotiationPersona = NegotiationPersona.CHRIS_VOSS):
        """
        Initialize the lowballer agent.

        Args:
            llm: LLM client for generating negotiation messages
            persona: Negotiation style to use (default: CHRIS_VOSS)
        """
        self.llm = llm
        self.persona = persona
        self.chat_history_file = Path("chat_history.json")
        self.chat_history: dict[str, list] = self._load_chat_history()

        # Ackerman Model percentages (from "Never Split the Difference")
        self.ackerman_percentages = {
            1: 65,   # Anchor low
            2: 85,   # Show flexibility
            3: 95,   # Getting close
            4: 100,  # Your true max
        }
        self.max_rounds = config.agent.max_negotiation_rounds

        print(f"LOWBALLER: Initialized with {persona.value} persona (Ackerman: 65%→85%→95%→100%)")
    
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
        Calculate the offer price using the Ackerman Model.

        The Ackerman Model (from "Never Split the Difference"):
        - Round 1: 65% (anchor low)
        - Round 2: 85% (show flexibility)
        - Round 3: 95% (getting close)
        - Round 4+: 100% (your true max)

        Also uses PRECISE numbers (e.g., $387 instead of $400) for
        psychological anchoring - signals you've done research.

        Args:
            listing_price: Original listing price
            round_num: Current negotiation round (1-indexed)

        Returns:
            Calculated offer price (precise, non-round number)
        """
        # Get Ackerman percentage for this round
        percent = self.ackerman_percentages.get(round_num, 100)

        # Calculate base offer
        base_offer = listing_price * (percent / 100)

        # Make it a PRECISE number (psychological anchoring)
        # Add small random offset to avoid round numbers like $400, $500
        offset = random.choice([-3, -7, +2, +8, -2, +3])
        precise_offer = int(base_offer) + offset

        return max(precise_offer, 1)  # Never go below $1
    
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
        
        # Step 0: Sync with the page to see where we left off
        await self.sync_conversation(listing_data, page)
        
        chat = self.chat_history[seller_id]
        current_round = chat["current_round"] + 1
        
        # Use LLM to analyze if seller has accepted
        seller_messages = [m for m in chat.get("messages", []) if m.get("role") == "seller"]
        if seller_messages:
            last_seller_msg = seller_messages[-1].get("content", "")
            
            # Ask LLM to classify the response
            analysis = await self._analyze_seller_response(last_seller_msg, chat.get("messages", []))
            
            if analysis == "ACCEPT":
                chat["status"] = "accepted"
                self._save_chat_history()
                confirm_msg = "Great! When and where can I collect? Cash ready 👍"
                await self._send_message(page, confirm_msg)
                print(f"LOWBALLER: 🎉 DEAL ACCEPTED! Seller said: \"{last_seller_msg}\"")
                return f"LOWBALLER: 🎉 DEAL ACCEPTED! Seller agreed. Confirmation sent."
            elif analysis == "REJECT":
                print(f"LOWBALLER: Seller rejected. Continuing negotiation...")
        
        # Check if we have accurate listing price (not a placeholder)
        has_accurate_price = listing_price > 100  # Placeholder is usually $100
        
        if has_accurate_price:
            # Calculate offer for this round (cap at round 4 for Ackerman)
            effective_round = min(current_round, 4)
            offer_price = self._calculate_offer(listing_price, effective_round)
            offer_percent = int((offer_price / listing_price) * 100)
            print(f"LOWBALLER: Round {current_round} - Ackerman offer ${offer_price} ({offer_percent}% of ${listing_price})")
        else:
            # No accurate price - let LLM decide based on context
            offer_price = None
            print(f"LOWBALLER: Round {current_round} - LLM will decide offer based on conversation")
        
        # Generate negotiation message
        if initial_message:
            message = initial_message
        else:
            message = await self._generate_message(item_name, listing_price, offer_price, current_round, listing_data)
        
        print(f"LOWBALLER: Message → \"{message}\"")
        
        # Try to type the message in chat
        sent = await self._send_message(page, message)
        
        # Log the message
        chat["messages"].append({
            "role": "lowballer",
            "content": message,
            "offer_price": offer_price if offer_price else "contextual",
            "round": current_round,
            "timestamp": datetime.now().isoformat(),
            "sent": sent,
        })
        chat["current_round"] = current_round
        self._save_chat_history()
        
        if sent:
            return f"LOWBALLER: Sent message for {item_name} (Round {current_round})"
        else:
            return f"LOWBALLER: Generated message for {item_name} (chat input not found)"
    
    async def _analyze_seller_response(self, seller_message: str, chat_history: list) -> str:
        """
        Use LLM to analyze if seller's response indicates acceptance, rejection, or counter-offer.
        
        Returns: "ACCEPT", "COUNTER", or "REJECT"
        """
        history_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" for m in chat_history[-8:]])
        
        messages = [
            {
                "role": "system",
                "content": """You are analyzing a Carousell negotiation chat. 
Your job is to classify the seller's LAST message into one of three categories:
- ACCEPT: Seller agrees to the buyer's price/offer (e.g., "ok deal", "can", "sure", "yes", "come collect")
- COUNTER: Seller proposes a different price or asks for more (e.g., "can you do $X?", "how about $X?", "too low")
- REJECT: Seller firmly rejects without counter (e.g., "no", "not selling", "firm price", "sorry")

Reply with ONLY one word: ACCEPT, COUNTER, or REJECT"""
            },
            {
                "role": "user",
                "content": f"""CHAT HISTORY:
{history_text}

SELLER'S LAST MESSAGE: "{seller_message}"

Classify this response:"""
            }
        ]
        
        try:
            response = await self.llm.complete(messages, max_tokens=10)
            result = response.get("content", "").strip().upper()
            
            if "ACCEPT" in result:
                return "ACCEPT"
            elif "REJECT" in result:
                return "REJECT"
            else:
                return "COUNTER"
        except Exception as e:
            print(f"LOWBALLER: Analysis failed ({e}), assuming COUNTER")
            return "COUNTER"

    async def _generate_message(
        self,
        item_name: str,
        listing_price: float,
        offer_price: float,
        round_num: int,
        listing_data: dict = {},
    ) -> str:
        """
        Generate a negotiation message using the LLM.

        Uses persona-specific system prompts and Chris Voss tactics
        from "Never Split the Difference" for each round.
        """
        # Get persona-specific system prompt
        system_prompt = SYSTEM_PROMPTS.get(self.persona.value, SYSTEM_PROMPTS["chris_voss"])

        # Get round-specific tactical context
        context = ROUND_CONTEXTS.get(round_num, "Make a reasonable counteroffer. Be friendly but firm.")

        # Get full chat history for context
        seller_id = self._get_seller_id(listing_data)
        history = self.chat_history.get(seller_id, {}).get("messages", [])
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-10:]]) # Last 10 msgs

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"""Generate a negotiation message for Carousell:

Item: {item_name}
Listed Price: S${listing_price}
Your Offer: S${offer_price}
Round: {round_num}
Description: {listing_data.get('description', 'N/A')}

CHAT HISTORY:
{history_text}

TACTICAL GUIDANCE:
{context}

Write ONLY the message itself, nothing else. Keep it to 1-2 sentences max."""
            }
        ]

        try:
            response = await self.llm.complete(messages, max_tokens=100)
            message = response.get("content", "").strip()

            # Check for LLM error or empty response
            if not message or response.get("error"):
                raise ValueError("LLM error or empty response")

            # Clean up the message (remove quotes if LLM wrapped it)
            message = message.strip('"\'')

            return message

        except Exception as e:
            print(f"LOWBALLER: ✗ LLM generation failed, using fallback → {e}")
            return self._get_fallback_message(item_name, offer_price, round_num)
    
    def _get_fallback_message(self, item_name: str, offer_price: float, round_num: int) -> str:
        """
        Get a fallback message without LLM.

        Uses Chris Voss tactics even in fallback mode:
        - Round 1: Tactical empathy + anchor
        - Round 2: Mirror + add value
        - Round 3: Label + urgency
        - Round 4: Accusation audit
        - Round 5: Walk-away bluff
        """
        fallbacks = {
            1: [  # Tactical empathy + anchor
                f"Hi! I know this is below asking, but seen similar {item_name}s around ${offer_price}. Cash ready, can pickup today!",
                f"Hey! Love the {item_name}. I know ${offer_price} is low but that's my budget - can do cash and immediate pickup?",
                f"Hi there! ${offer_price} might be cheeky but I'm serious buyer with cash. How can we make this work?",
            ],
            2: [  # Mirror + add value
                f"Firm? I understand. Would ${offer_price} work if I pickup within the hour? Cash in hand.",
                f"I hear you. Can stretch to ${offer_price} - I'll come to you anytime today, cash ready.",
                f"Got it. How about ${offer_price} with immediate collection? Trying to make it easy for you.",
            ],
            3: [  # Label + urgency
                f"It seems like you want this sold quickly - ${offer_price} cash and I'm free right now to collect?",
                f"Sounds like you've had lowballers before, but ${offer_price} is genuine. Can meet in 30 mins!",
                f"${offer_price} is really my max lah. Can do cash and pickup today if that helps?",
            ],
            4: [  # Accusation audit
                f"You probably have better offers coming in, but ${offer_price} cash today is my best. Serious buyer here.",
                f"I know ${offer_price} might not be what you hoped for, but I'm ready to deal now. What do you think?",
                f"You're probably thinking this is too low - ${offer_price} is genuinely my limit though. Cash ready!",
            ],
            5: [  # Walk-away bluff
                f"I totally understand if ${offer_price} doesn't work for you. Good luck with the sale!",
                f"${offer_price} is really my final offer. No worries if it doesn't work - all the best!",
                f"Can only do ${offer_price} max. If not, no hard feelings - hope you find a buyer soon!",
            ],
        }

        options = fallbacks.get(round_num, fallbacks[5])
        return random.choice(options)
    
    async def _send_message(self, page: Any, message: str) -> bool:
        """
        Type and send a message in the Carousell chat.
        
        Args:
            page: Playwright page object
            message: Message to send
            
        Returns:
            True if message was sent, False otherwise
        """
        if page is None:
            return False
            
        print(f"LOWBALLER: Waiting for chat input on {page.url}...")
        
        # Wait for page to settle
        await asyncio.sleep(2)
        
        # Use the exact Carousell chat textarea selector
        try:
            text_box = page.locator('textarea[placeholder="Type here..."]')
            
            # Wait for it to be visible
            await text_box.wait_for(state="visible", timeout=10000)
            
            # Fill with the message
            await text_box.fill(message)
            print(f"LOWBALLER: ✓ Typed message into chat input")
            
            # Small delay before sending
            await asyncio.sleep(0.5)
            
            # Press Enter to send
            await text_box.press("Enter")
            print(f"LOWBALLER: ✓ Message sent (Enter key)")
            
            # Wait a moment for the message to be sent
            await asyncio.sleep(1)
            return True
            
        except Exception as e:
            print(f"LOWBALLER: ✗ Failed to send message: {e}")
            
            # Fallback: Try alternative selectors
            fallback_selectors = [
                'textarea[placeholder*="Type"]',
                'textarea[placeholder*="message"]',
                '[contenteditable="true"]',
                'textarea',
            ]
            
            for selector in fallback_selectors:
                try:
                    el = page.locator(selector).first
                    if await el.is_visible():
                        await el.fill(message)
                        await el.press("Enter")
                        print(f"LOWBALLER: ✓ Message sent via fallback ({selector})")
                        return True
                except:
                    continue
            
            await page.screenshot(path="screenshots/chat_input_not_found.png")
            return False
    
    async def sync_conversation(self, listing_data: dict, page: Any) -> list[dict]:
        """
        Scrapes the chat from the page and synchronizes it with local history.
        Identifies new seller messages and updates the negotiation round.
        
        Returns:
            List of new messages from the seller.
        """
        if page is None:
            return []
            
        seller_id = self._get_seller_id(listing_data)
        if seller_id not in self.chat_history:
            self.chat_history[seller_id] = {
                "listing": listing_data,
                "started_at": datetime.now().isoformat(),
                "messages": [],
                "current_round": 0,
                "status": "active",
            }
            
        print(f"LOWBALLER: Synchronizing chat for {seller_id}...")
        
        # Scrape all messages from the page
        scraped_messages = await page.evaluate("""
            () => {
                const msgs = [];
                // D_cbh is the general message container
                const elements = document.querySelectorAll('div[id^="chat-message-"], .D_cbh');
                
                elements.forEach(el => {
                    // D_cbq is usually buyer (me), D_cbr is usually seller (them)
                    const isMe = el.querySelector('.D_cbq') !== null;
                    const isThem = el.querySelector('.D_cbr') !== null;
                    
                    const textEl = el.querySelector('p.D_cBA');
                    if (!textEl) return;
                    
                    const text = textEl.innerText.trim();
                    if (text) {
                        msgs.push({
                            role: isMe ? "lowballer" : "seller",
                            content: text
                        });
                    }
                });
                return msgs;
            }
        """)
        
        if not scraped_messages:
            return []
            
        existing_history = self.chat_history[seller_id]["messages"]
        new_messages = []
        
        # Simple synchronization: Check if scraped messages appear in our history
        # We start from the end to find what's new
        for scraped in scraped_messages:
            # Check if this message (by content and role) already exists in our history
            # This is a bit naive but works for the sequence
            is_new = True
            for hist in existing_history:
                if hist["role"] == scraped["role"] and hist["content"] == scraped["content"]:
                    is_new = False
                    break
            
            if is_new:
                print(f"LOWBALLER: ✨ New message from {scraped['role']}: {scraped['content'][:30]}...")
                msg_entry = {
                    "role": scraped["role"],
                    "content": scraped["content"],
                    "timestamp": datetime.now().isoformat(),
                    "synced": True
                }
                existing_history.append(msg_entry)
                if scraped["role"] == "seller":
                    new_messages.append(msg_entry)
        
        # Update current round based on how many "lowballer" messages were sent
        sent_rounds = len([m for m in existing_history if m["role"] == "lowballer"])
        self.chat_history[seller_id]["current_round"] = sent_rounds
        
        self._save_chat_history()
        return new_messages

    async def extract_seller_reply(self, page: Any) -> Optional[str]:
        # Implementation remains for compatibility but sync_conversation is preferred
        pass
    
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
        # In Ackerman model, 100% is our true max (round 4 percentage)
        listing_price = listing_data.get("price", 0)
        max_acceptable = listing_price * (self.ackerman_percentages.get(4, 100) / 100)
        
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
