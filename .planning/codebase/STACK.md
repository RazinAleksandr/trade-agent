# Technology Stack

**Analysis Date:** 2026-03-25

## Languages

**Primary:**
- Python 3.12.9 - All source code, trading logic, analysis, and data persistence

## Runtime

**Environment:**
- Python 3.12.9
- Virtual environment: `.venv/` (committed: no)

**Package Manager:**
- pip (standard Python package manager)
- Lockfile: `requirements.txt` (present, pinned versions listed below)

## Frameworks

**Core Trading:**
- `py-clob-client` (>=0.17.0) - Polymarket CLOB API client; handles order placement, position management, market data; core integration for live trading
- `web3` (>=7.0.0) - Ethereum/Polygon wallet interaction, token approvals, RPC connectivity for L2 operations

**Analysis & LLM:**
- `anthropic` (>=0.49.0) - AI integration (mentioned in requirements, may be deprecated in favor of OpenAI)
- `openai` (via OpenAI SDK, configured in code) - GPT-4o API for market probability estimation via Responses API with web search tool

**HTTP & Data:**
- `requests` (>=2.31.0) - Gamma API HTTP client for market discovery and metadata
- `python-dotenv` (>=1.0.0) - Environment variable loading from `.env` files

**Cryptography & Wallet:**
- `eth-account` (>=0.13.0) - Ethereum wallet generation, account management, transaction signing for Polygon mainnet

## Key Dependencies

**Critical:**
- `py-clob-client` (>=0.17.0) - Core trading execution; derives L2 API credentials, creates signed orders, posts to CLOB API
- `openai` - Market analysis engine; uses GPT-4o Responses API with `web_search` tool for real-time data
- `web3` (>=7.0.0) - Token approvals and on-chain operations for live trading (USDC approve, CTF setApprovalForAll)

**Infrastructure:**
- `requests` (>=2.31.0) - Gamma API HTTP requests for market discovery and event fetching
- `eth-account` (>=0.13.0) - Wallet generation and signing for EOA transactions
- `python-dotenv` (>=1.0.0) - Configuration management via environment variables

## Configuration

**Environment:**
- Configuration via `.env` file (must exist, must never be committed)
- All parameters loaded through `config.py` via `python-dotenv`
- Example `.env` contents (never commit secrets):
  ```
  OPENAI_API_KEY=sk-...
  PRIVATE_KEY=0x...
  PAPER_TRADING=true
  CHAIN_ID=137
  ```

**Build:**
- No build step required; Python runs directly
- `setup_wallet.py` is initialization script for live trading only (one-time use)

## Platform Requirements

**Development:**
- Python 3.12.9
- Virtual environment (`.venv/`)
- macOS, Linux, or Windows
- Internet connectivity for:
  - Gamma API (`https://gamma-api.polymarket.com`)
  - CLOB API (`https://clob.polymarket.com`)
  - OpenAI API (`https://api.openai.com`)
  - Polygon RPC (`https://polygon-rpc.com`)

**Production:**
- Python 3.12.9 runtime
- Polygon mainnet chain ID: 137
- OPENAI_API_KEY required for market analysis
- PRIVATE_KEY required for live trading (optional for paper trading)
- SQLite3 (embedded in Python stdlib)
- Network access to all external APIs (see INTEGRATIONS.md)

---

*Stack analysis: 2026-03-25*
