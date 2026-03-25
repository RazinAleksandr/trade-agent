# Wallet Setup

This guide covers setting up a wallet for live trading on Polymarket. **Not needed for paper trading.**

## Prerequisites

- MATIC on Polygon (for gas fees)
- USDC on Polygon (for trading)
- A funded Polygon wallet, or the agent can generate one for you

## Quick Setup

```bash
source .venv/bin/activate
python setup_wallet.py
```

The interactive script will:

1. **Check for existing key** — looks for `PRIVATE_KEY` in `.env`
2. **Generate or import wallet** — creates a new Ethereum wallet or accepts your existing private key
3. **Save to `.env`** — optionally writes the key to your `.env` file
4. **Derive API credentials** — creates L2 credentials for Polymarket's CLOB API
5. **Set token allowances** — approves the exchange contracts to spend your USDC and CTF tokens

## Step-by-Step

### 1. Generate a Wallet

If you don't have a wallet, the script generates one:

```
Address:     0x1234...abcd
Private Key: 0xdeadbeef...
```

Save the private key securely. If you lose it, you lose access to any funds.

### 2. Fund the Wallet

Send funds to the wallet address on **Polygon** (not Ethereum mainnet):

- **MATIC** — for gas fees (~0.1 MATIC is enough for many transactions)
- **USDC** — for placing trades (the amount you want to trade with)

You can bridge from Ethereum mainnet using the [Polygon Bridge](https://portal.polygon.technology/bridge) or buy directly on Polygon via an exchange.

### 3. Derive API Credentials

The script derives L2 API credentials from your private key:

```
API Key:    abc123...
Secret:     def456...
Passphrase: ghi789...
```

These are derived deterministically — running the script again with the same private key produces the same credentials. You don't need to save them separately.

### 4. Set Token Allowances

The script sets four on-chain approvals (each costs a small amount of MATIC):

| Approval | Contract | Purpose |
|---|---|---|
| USDC → Exchange | ERC20 `approve` | Allow Exchange to spend USDC |
| USDC → NegRisk Exchange | ERC20 `approve` | Allow NegRisk Exchange to spend USDC |
| CTF → Exchange | ERC1155 `setApprovalForAll` | Allow Exchange to transfer outcome tokens |
| CTF → NegRisk Exchange | ERC1155 `setApprovalForAll` | Allow NegRisk Exchange to transfer outcome tokens |

Both exchanges need allowances because Polymarket uses a separate contract for neg-risk markets.

### 5. Enable Live Trading

Edit `.env`:

```env
PRIVATE_KEY=0xYourPrivateKey
PAPER_TRADING=false
```

Then run:

```bash
python main.py
```

## Using an Existing Wallet

If you already have a Polygon wallet (e.g., from MetaMask):

1. Export the private key from your wallet
2. Add it to `.env`: `PRIVATE_KEY=0x...`
3. Run `python setup_wallet.py` — it will skip generation and proceed to credential derivation and allowances

## Security Notes

- **Never share your private key.** Anyone with the key has full access to the wallet.
- **The `.env` file is gitignored.** Never commit it to version control.
- The private key is an EOA (Externally Owned Account) key — `signature_type=0`.
- Consider using a dedicated wallet for this agent, not your main wallet.
- Start with small amounts of USDC to verify everything works before scaling up.

## Troubleshooting

**"Failed to derive credentials"**
- Check that `POLYMARKET_HOST` is correct (`https://clob.polymarket.com`)
- Ensure your network can reach the CLOB API

**"ERROR setting allowances"**
- Ensure the wallet has MATIC for gas
- Check Polygon RPC connectivity (`https://polygon-rpc.com`)
- You can set allowances manually via Polygonscan if needed

**"web3 not installed"**
- Run `pip install web3` — it's needed for the allowance transactions
