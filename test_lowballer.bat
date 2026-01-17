@echo off
REM Test Lowballer Agent with Ollama
REM This tests lowball message generation

echo ============================================
echo LOWBALLER AGENT TEST
echo ============================================
echo.
echo Testing lowball message generation...
echo.

ollama run phi3 "You are negotiating on Carousell Singapore. Generate a lowball message for:

Item: iPhone 14 Pro 256GB
Listed Price: S$800
Your Offer: S$400 (50%% of listed price)
Round: 1 (First message)

Rules:
- Keep message short (1-2 sentences)
- Be friendly but firm on price
- Mention cash payment and quick pickup
- Sound natural, not like a bot

Write just the message, nothing else."

echo.
echo ============================================

echo.
echo Testing counter-offer response...
echo.

ollama run phi3 "The seller replied: 'Sorry, lowest I can go is $700'

You are negotiating on Carousell. Generate your counter-offer:

Item: iPhone 14 Pro 256GB
Original Price: S$800
Seller's Counter: S$700
Your New Offer: S$480 (60%% - increased from 50%%)
Round: 2

Write just the message, nothing else. Be polite but firm."

echo.
echo ============================================
echo TEST COMPLETE
echo ============================================
pause
