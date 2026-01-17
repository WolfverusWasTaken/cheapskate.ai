@echo off
REM Test Controller Agent with Ollama
REM This tests the tool-calling capabilities of the controller

echo ============================================
echo CONTROLLER AGENT TEST
echo ============================================
echo.
echo Testing Ollama with controller tool-calling prompt...
echo.

ollama run phi3 "You are the Controller agent for Carousell automation. You have these tools available:

1. search_carousell(query) - Search for items
2. extract_listings() - Get listings from page  
3. open_chat(seller_index) - Open seller chat
4. delegate_lowball(seller_index) - Start negotiation

User request: Find iPhone 14 deals under $3000

Based on this request, what tools would you call and in what order? Explain your reasoning."

echo.
echo ============================================
echo TEST COMPLETE
echo ============================================
pause
