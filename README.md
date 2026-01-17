# 🔥 Carousell Lowballer Agent

An AI-powered web automation agent that finds listings on Carousell Singapore and negotiates lowball offers automatically.

## 🚀 Features

- **Visible Browser Automation**: Watch the agent work in real-time with a visible Chromium browser
- **AI-Powered Negotiation**: Uses LLMs (Ollama/Gemini) to generate natural negotiation messages
- **Modular Architecture**: 6 independently testable modules for easy development
- **CLI Control**: Interactive command-line interface for controlling the agent
- **Chat History Logging**: All negotiations saved to `chat_history.json`
- **LLM Switching**: Switch between Ollama (local) and Gemini (cloud) via `.env`

## 📁 Project Structure

```
CrackDSabR/
├── main.py              # Entry point - CLI interface
├── browser_loader.py    # Module 1: Playwright browser management
├── dom_extractor.py     # Module 2: DOM extraction + screenshots
├── dom_parser.py        # Module 3: Carousell listing parser
├── controller.py        # Module 4: Main orchestrating agent
├── lowballer.py         # Module 5: Negotiation agent
├── llm_factory.py       # LLM abstraction (Ollama/Gemini)
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── setup.bat            # One-click setup script
├── start.bat            # Launch the agent
└── test_*.bat           # Individual module tests
```

## ⚡ Quick Start

### 1. Setup

```bash
# Run the setup script (installs dependencies + Playwright)
setup.bat

# Or manually:
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

### 2. Configure LLM

Edit `.env` to set your LLM provider:

```env
# For Ollama (local, free)
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini

# For Gemini (cloud)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
```

### 3. Run

```bash
# Start the agent
python main.py

# Or use the launcher
start.bat
```

## 🎮 Usage

Once running, use these commands:

```
>>> find iPhone 14 under $600     # Search for items
>>> listings                       # Show extracted listings
>>> lowball 0                      # Negotiate on listing #0
>>> chat 1                         # Open chat for listing #1
>>> screenshot                     # Capture current page
>>> history                        # Show negotiation history
>>> help                           # Show all commands
>>> quit                           # Exit
```

## 🧪 Testing

Each module can be tested independently:

```bash
# Test all modules (no browser)
run_tests.bat

# Test browser automation
test_browser.bat

# Test with Ollama LLM
test_controller.bat
test_lowballer.bat

# Test DOM parsing
test_parser.bat
```

## 🛠️ Module Details

### Module 1: `browser_loader.py`
- Launches Playwright Chromium with anti-detection
- Provides shared page access across modules
- Handles navigation and screenshots

### Module 2: `dom_extractor.py`
- Captures full HTML + screenshots
- Returns structured dict with metadata
- Extracts visible text content

### Module 3: `dom_parser.py`
- Parses Carousell-specific HTML structure
- Extracts listings with price, seller, URLs
- Provides price filtering

### Module 4: `controller.py`
- Main agent with LLM tool-calling
- Tools: search, extract, open_chat, delegate_lowball
- Manages conversation history

### Module 5: `lowballer.py`
- Strategic negotiation (50% → 70% max)
- Generates natural messages via LLM
- Logs all chats to JSON

### Module 6: `main.py`
- CLI interface with help system
- Wires all modules together
- Graceful shutdown handling

## 📊 Negotiation Strategy

The Lowballer uses this escalation strategy:

| Round | Offer % | Example ($800 item) |
|-------|---------|---------------------|
| 1     | 50%     | $400                |
| 2     | 60%     | $480                |
| 3     | 70%     | $560 (max)          |
| 4+    | 70%     | Walk away if rejected |

## ⚠️ Disclaimer

This tool is for educational purposes. Use responsibly and in accordance with Carousell's Terms of Service. Automated interactions may be against platform policies.

## 📝 License

MIT License - Use at your own risk.
