# API Reference

The agent interacts with three external APIs: Polymarket Gamma (market data), Polymarket CLOB (trading), and OpenAI (analysis).

## Polymarket Gamma API

**Base URL:** `https://gamma-api.polymarket.com`

Used for market discovery and metadata. Public, no authentication required.

### GET /markets

Fetches list of markets with metadata.

```
GET /markets?closed=false&active=true&order=volume24hr&ascending=false&limit=50
```

**Response fields used:**
| Field | Type | Notes |
|---|---|---|
| `id` | string | Market ID |
| `conditionId` | string | On-chain condition ID |
| `question` | string | Market question |
| `description` | string | Full description |
| `category` | string | Category tag |
| `clobTokenIds` | string | **Stringified JSON array** — must `json.loads()` |
| `outcomePrices` | string | **Stringified JSON array** — must `json.loads()` |
| `volume24hr` | float | 24-hour volume in USDC |
| `liquidityClob` | float | Available liquidity |
| `endDate` | string | Resolution date |
| `active` | bool | Market is active |
| `closed` | bool | Market has resolved |

**Important:** `clobTokenIds` and `outcomePrices` are JSON strings within the JSON response. You must parse them with `json.loads()`:
```python
token_ids = json.loads(market["clobTokenIds"])    # ["token_yes", "token_no"]
prices = json.loads(market["outcomePrices"])       # ["0.65", "0.35"]
```

### GET /markets/{id}

Fetches a single market by ID. Same response format.

### GET /events

Fetches active events (groups of related markets).

```
GET /events?closed=false&active=true&order=volume24hr&ascending=false&limit=10
```

## Polymarket CLOB API

**Base URL:** `https://clob.polymarket.com`

Used for order placement and position management. Requires authentication.

### Authentication

Three-step process:

```python
from py_clob_client.client import ClobClient

# 1. Initialize with L1 private key
client = ClobClient(
    host="https://clob.polymarket.com",
    key="0xYourPrivateKey",
    chain_id=137,
    signature_type=0,  # 0 = EOA wallet
)

# 2. Derive L2 API credentials
creds = client.create_or_derive_api_creds()

# 3. Set credentials for authenticated requests
client.set_api_creds(creds)
```

**Signature types:**
| Value | Meaning |
|---|---|
| 0 | EOA wallet (standard Ethereum wallet) |
| 1 | Magic/email wallet |
| 2 | Browser proxy |

This agent uses **type 0** (EOA).

### Order Placement

```python
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

order_args = OrderArgs(
    token_id="0x...",     # YES or NO token ID from Gamma API
    price=0.65,           # Limit price (0.0-1.0)
    size=10.0,            # Number of shares
    side=BUY,             # Always BUY the side we believe in
)

signed_order = client.create_order(order_args)
result = client.post_order(signed_order, OrderType.GTC)
```

**Order types:**
| Type | Behavior |
|---|---|
| `GTC` | Good-Till-Cancelled — stays on book until filled or cancelled |
| `FOK` | Fill-Or-Kill — fills entirely or cancels |
| `GTD` | Good-Till-Date — expires at specified time |

This agent uses **GTC** for better price execution.

### Other Endpoints

```python
client.get_ok()              # Health check
client.get_server_time()     # Server timestamp
client.get_orders()          # Get open orders
client.cancel(order_id)      # Cancel an order
client.get_positions()       # Get current positions
client.get_midpoint(token_id)  # Get orderbook midpoint price
```

## OpenAI API

**SDK:** `openai` Python package
**API:** Responses API (`client.responses.create()`)

### Initialization

```python
from openai import OpenAI

client = OpenAI(api_key="sk-proj-...")
```

### Market Analysis Call

```python
response = client.responses.create(
    model="gpt-4o",
    input="<analysis prompt with market details>",
    tools=[{"type": "web_search"}],  # Optional, enabled by default
)

text = response.output_text  # Plain text response
```

The `web_search` tool gives the model the ability to search the web during analysis. The model decides when and what to search — there's no explicit search query from the agent.

### Response Format

The prompt instructs GPT-4o to return JSON:

```json
{
    "estimated_probability": 0.72,
    "confidence": 0.8,
    "reasoning": "Recent polls show...",
    "key_factors": ["factor1", "factor2", "factor3"],
    "information_edge": "Market may be underweighting...",
    "sources_consulted": ["https://...", "Reuters report on..."]
}
```

The response parser handles three formats:
1. Raw JSON
2. JSON inside markdown code blocks (` ```json ... ``` `)
3. JSON embedded in free text (regex extraction)

## Polygon Blockchain

**Chain:** Polygon mainnet (chain_id: 137)
**RPC:** `https://polygon-rpc.com`

Used only by `setup_wallet.py` for setting token allowances.

### Contract Addresses

| Contract | Address |
|---|---|
| USDC (ERC20) | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` |
| CTF (ERC1155) | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` |
| Exchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` |
| NegRisk Exchange | `0xC5d563A36AE78145C45a50134d48A1215220f80a` |

### Required Allowances

Before live trading, four approval transactions are needed:

1. **USDC → Exchange** — `approve(Exchange, MAX_UINT256)`
2. **USDC → NegRisk Exchange** — `approve(NegRiskExchange, MAX_UINT256)`
3. **CTF → Exchange** — `setApprovalForAll(Exchange, true)`
4. **CTF → NegRisk Exchange** — `setApprovalForAll(NegRiskExchange, true)`

The `setup_wallet.py` script handles all four automatically.
