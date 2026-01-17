# 🔥 Carousell Lowballer Agent

An AI-powered web automation agent that finds listings on Carousell Singapore and negotiates lowball offers automatically.

---

## � Team Structure & Responsibilities

This project is split across **3 developers**. Each can work **independently** using mock modules for testing.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │    DEV 1     │     │    DEV 2     │     │    DEV 3     │   │
│   │  (You/Lead)  │────▶│  Controller  │────▶│  Lowballer   │   │
│   │              │     │    Agent     │     │    Agent     │   │
│   └──────────────┘     └──────────────┘     └──────────────┘   │
│          │                    │                    │            │
│          ▼                    ▼                    ▼            │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │browser_loader│     │ controller.py│     │ lowballer.py │   │
│   │dom_extractor │     │              │     │              │   │
│   │ dom_parser   │     │Uses mocks or │     │Uses mocks or │   │
│   │              │     │ real browser │     │  real page   │   │
│   └──────────────┘     └──────────────┘     └──────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 👤 DEV 1 (You - Lead Developer)

### Your Modules
| File | Purpose |
|------|---------|
| `browser_loader.py` | Playwright browser management |
| `dom_extractor.py` | DOM capture + screenshots |
| `dom_parser.py` | Carousell listing extraction |
| `main.py` | Main entry point |

### Your Test Command
```bash
python dev1_test_browser.py

# Or test individual components:
python dev1_test_browser.py --browser    # Browser only
python dev1_test_browser.py --extractor  # Extractor only
python dev1_test_browser.py --parser     # Parser only
python dev1_test_browser.py --full       # Full integration
```

### Key Interfaces to Maintain
Dev 2 and Dev 3 depend on these interfaces:

```python
# browser_loader.py
class BrowserLoader:
    async def launch() -> (browser, context, page)
    def get_page() -> Page
    async def navigate(url: str) -> bool
    async def screenshot(path: str) -> str
    async def close() -> None

# dom_extractor.py
async def extract_dom(page) -> dict:
    # Returns: {"html": str, "screenshot": str, "url": str, "timestamp": str}

# dom_parser.py
def parse_listings(dom_data: dict) -> list[dict]:
    # Returns: [{"index", "title", "price", "price_raw", "seller_name", "listing_url", "chat_selector"}]
```

---

## 👤 DEV 2 (Controller Agent)

### Your Module
| File | Purpose |
|------|---------|
| `controller.py` | Main orchestrating agent with tool-calling |

### How to Test (WITHOUT needing Dev 1's code)
```bash
# Uses mock browser/DOM automatically
python dev2_test_controller.py
```

### Toggle Between Mock and Real
In `dev2_test_controller.py`:
```python
# Set to False once Dev 1's code is ready
USE_MOCKS = True   # True = use mock browser
USE_MOCKS = False  # False = use real browser
```

### Your Responsibilities
1. **Tool Definitions** - Define tools in `_define_tools()`
2. **Tool Handlers** - Implement handlers in `_define_tool_handlers()`
3. **LLM Loop** - Process prompts → execute tools → return results
4. **Delegation** - Call Lowballer agent via `delegate_lowball`

### Available Mock Data
The mock modules provide:
- 5 pre-defined iPhone listings (prices: $350-$1200)
- Simulated page navigation
- Fake screenshots

### Key Methods to Implement/Modify
```python
class ControllerAgent:
    async def run(user_prompt: str) -> str
    async def _handle_search(query: str, max_price: float) -> str
    async def _handle_extract() -> str
    async def _handle_open_listing(listing_index: int) -> str
    async def _handle_open_chat(listing_index: int) -> str
    async def _handle_delegate_lowball(listing_index: int) -> str
```

---

## 👤 DEV 3 (Lowballer/Negotiator Agent)

### Your Module
| File | Purpose |
|------|---------|
| `lowballer.py` | Negotiation agent with strategic offers |

### How to Test (WITHOUT needing browser or controller)
```bash
# Uses mock data automatically
python dev3_test_lowballer.py
```

### Your Responsibilities
1. **Offer Strategy** - 50% → 60% → 70% escalation
2. **Message Generation** - Natural negotiation messages via LLM
3. **Chat History** - Track all negotiations in `chat_history.json`
4. **Counter-Offers** - Handle seller responses

### Key Methods to Implement/Modify
```python
class LowballerAgent:
    async def negotiate(listing_data: dict, page: Any) -> str
    def _calculate_offer(listing_price: float, round_num: int) -> float
    async def _generate_message(item_name, price, offer, round) -> str
    async def _send_message(page, message: str) -> bool
    async def respond_to_counter(listing_data, page, seller_price) -> str
```

### Negotiation Strategy
```
Round 1: 50% of listed price  ($800 item → offer $400)
Round 2: 60% of listed price  ($800 item → offer $480)
Round 3: 70% of listed price  ($800 item → offer $560)
Round 4+: 70% max, then walk away
```

---

## 📁 Project Structure

```
CrackDSabR/
├── 📂 mocks/                    # Mock modules for independent testing
│   ├── __init__.py
│   ├── mock_browser.py          # Fake browser for Dev 2/3
│   └── mock_dom.py              # Fake DOM data for Dev 2/3
│
├── 📄 browser_loader.py         # [DEV 1] Browser management
├── 📄 dom_extractor.py          # [DEV 1] DOM extraction
├── 📄 dom_parser.py             # [DEV 1] Listing parser
├── 📄 controller.py             # [DEV 2] Controller agent
├── 📄 lowballer.py              # [DEV 3] Negotiation agent
├── 📄 llm_factory.py            # LLM abstraction (shared)
├── 📄 config.py                 # Configuration (shared)
├── 📄 main.py                   # Entry point
│
├── 📄 dev1_test_browser.py      # [DEV 1] Your test script
├── 📄 dev2_test_controller.py   # [DEV 2] Controller tests
├── 📄 dev3_test_lowballer.py    # [DEV 3] Lowballer tests
│
├── 📄 requirements.txt
├── 📄 .env / .env.example
└── 📄 README.md
```

---

## ⚡ Quick Start

### 1. Setup (Everyone)
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Create .env file
copy .env.example .env
```

### 2. Configure LLM
Edit `.env`:
```env
# For Ollama (local, recommended for testing)
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini

# For Gemini (cloud)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-api-key-here
```

### 3. Test Your Module
```bash
# Dev 1:
python dev1_test_browser.py

# Dev 2:
python dev2_test_controller.py

# Dev 3:
python dev3_test_lowballer.py
```

### 4. Run Full Agent (Integration)
```bash
python main.py
```

---

## 🔄 Integration Workflow

### Phase 1: Independent Development (Parallel)
```
Dev 1: Works on browser_loader, dom_extractor, dom_parser
Dev 2: Works on controller.py using mocks
Dev 3: Works on lowballer.py using mocks
```

### Phase 2: Integration Testing
```
1. Dev 1 completes browser modules
2. Dev 2 sets USE_MOCKS = False, tests with real browser
3. Dev 3 tests lowballer with real page object
4. Run: python main.py
```

### Phase 3: End-to-End Testing
```bash
$ python main.py
[Visible Chromium opens to carousell.sg]

>>> find people selling iPhone 14 under $3000
[AGENT: Navigating to search... Extracting 5 listings...]

>>> lowball 0
[LOWBALLER: "Hi! iPhone looks great. Can do $300 cash?"]
```

---

## 🧪 Test Ollama Integration

Make sure Ollama is running with phi3:
```bash
# Check Ollama is running
ollama list

# Pull phi3 if needed
ollama pull phi3:mini

# Test controller reasoning
ollama run phi3 "You are a Carousell automation controller. Tools: search_carousell, extract_listings, open_chat. User says: Find iPhones under $500. What tools do you call?"

# Test lowball message
ollama run phi3 "Generate a short lowball message for iPhone 14 at $800. Offer $400 cash. Be friendly."
```

---

## 📊 Data Flow

```
User Input ("find iPhone under $3000")
       │
       ▼
┌─────────────────┐
│   Controller    │  ← [DEV 2]
│   (LLM + Tools) │
└────────┬────────┘
         │ calls search_carousell()
         ▼
┌─────────────────┐
│ BrowserLoader   │  ← [DEV 1]
│   navigate()    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DOM Extractor  │  ← [DEV 1]
│  extract_dom()  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   DOM Parser    │  ← [DEV 1]
│ parse_listings()│
└────────┬────────┘
         │ returns listings
         ▼
┌─────────────────┐
│   Controller    │  ← [DEV 2]
│delegate_lowball │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Lowballer     │  ← [DEV 3]
│   negotiate()   │
└────────┬────────┘
         │
         ▼
   Chat History JSON
```

---

## ⚠️ Important Notes

1. **Mock Toggle**: Dev 2 and Dev 3 - remember to set `USE_MOCKS = False` when integrating
2. **Interface Contracts**: Dev 1 - don't change the function signatures without telling the team
3. **Chat History**: All negotiations save to `chat_history.json` - commit this for demos
4. **Visible Browser**: Default is `headless=False` so you can watch the agent work

---

## 📝 License

MIT License - Educational use. Use responsibly per Carousell ToS.
