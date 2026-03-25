#!/usr/bin/env python3
"""
One-time wallet setup script.
- Generates or imports a wallet
- Derives L2 API credentials from the private key
- Sets token allowances (USDC + CTF) for both exchanges
- Tests connectivity to the CLOB API
"""

import sys
import os
from eth_account import Account
from py_clob_client.client import ClobClient
from dotenv import load_dotenv, set_key

load_dotenv()

POLYMARKET_HOST = os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com")
CHAIN_ID = int(os.getenv("CHAIN_ID", "137"))

# Polygon mainnet contract addresses
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEG_RISK_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"


def generate_wallet():
    """Generate a new Ethereum wallet."""
    account = Account.create()
    print(f"Address:     {account.address}")
    print(f"Private Key: {account.key.hex()}")
    print("\nIMPORTANT: Save this private key securely!")
    print("You need to fund this address with MATIC (for gas) and USDC on Polygon.")
    return account.key.hex()


def derive_api_credentials(private_key: str):
    """Derive Polymarket L2 API credentials from private key."""
    print("\nDeriving API credentials...")
    try:
        client = ClobClient(
            POLYMARKET_HOST,
            key=private_key,
            chain_id=CHAIN_ID,
            signature_type=0,  # 0=EOA wallet
        )
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)

        print(f"API Key:    {creds.api_key}")
        print(f"Secret:     {creds.api_secret}")
        print(f"Passphrase: {creds.api_passphrase}")

        # Test connectivity
        ok = client.get_ok()
        print(f"\nCLOB API check: {ok}")

        server_time = client.get_server_time()
        print(f"Server time: {server_time}")

        return creds
    except Exception as e:
        print(f"ERROR: Failed to derive credentials: {e}")
        return None


def set_token_allowances(private_key: str):
    """Set USDC and CTF token allowances for both exchange contracts."""
    print("\nSetting token allowances...")
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
        account = w3.eth.account.from_key(private_key)
        MAX_INT = 2**256 - 1

        ERC20_ABI = [{"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}]
        ERC1155_ABI = [{"inputs": [{"name": "operator", "type": "address"}, {"name": "approved", "type": "bool"}], "name": "setApprovalForAll", "outputs": [], "type": "function"}]

        usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=ERC20_ABI)
        ctf = w3.eth.contract(address=Web3.to_checksum_address(CTF_ADDRESS), abi=ERC1155_ABI)
        nonce = w3.eth.get_transaction_count(account.address)

        approvals = [
            ("USDC → Exchange", usdc.functions.approve(Web3.to_checksum_address(EXCHANGE_ADDRESS), MAX_INT)),
            ("USDC → NegRisk Exchange", usdc.functions.approve(Web3.to_checksum_address(NEG_RISK_EXCHANGE), MAX_INT)),
            ("CTF → Exchange", ctf.functions.setApprovalForAll(Web3.to_checksum_address(EXCHANGE_ADDRESS), True)),
            ("CTF → NegRisk Exchange", ctf.functions.setApprovalForAll(Web3.to_checksum_address(NEG_RISK_EXCHANGE), True)),
        ]

        for i, (label, func) in enumerate(approvals):
            tx = func.build_transaction({
                "from": account.address,
                "nonce": nonce + i,
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
            })
            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  {label}: {tx_hash.hex()}")

        print("Allowances set! Waiting for confirmations...")
        return True

    except ImportError:
        print("web3 not installed — skipping allowance setup")
        return False
    except Exception as e:
        print(f"ERROR setting allowances: {e}")
        print("You may need to set allowances manually or ensure wallet has MATIC for gas.")
        return False


def main():
    print("=" * 50)
    print("Polymarket Wallet Setup")
    print("=" * 50)

    private_key = os.getenv("PRIVATE_KEY", "")

    if not private_key or private_key == "0x...":
        print("\nNo private key found in .env")
        choice = input("Generate new wallet? (y/n): ").strip().lower()
        if choice == "y":
            private_key = generate_wallet()
            save = input("\nSave to .env? (y/n): ").strip().lower()
            if save == "y":
                env_path = os.path.join(os.path.dirname(__file__), ".env")
                if not os.path.exists(env_path):
                    with open(env_path, "w") as f:
                        f.write("")
                set_key(env_path, "PRIVATE_KEY", private_key)
                print("Saved to .env")
        else:
            private_key = input("Enter your private key (with 0x prefix): ").strip()

    if not private_key:
        print("No private key provided. Exiting.")
        sys.exit(1)

    # Derive API credentials
    creds = derive_api_credentials(private_key)

    if creds:
        # Set token allowances
        choice = input("\nSet token allowances on Polygon? (requires MATIC for gas) (y/n): ").strip().lower()
        if choice == "y":
            set_token_allowances(private_key)

        print("\n✓ Setup complete! You can now run the trading agent.")
        print("\nNext steps:")
        print("1. Fund your wallet with MATIC + USDC on Polygon")
        print("2. Set OPENAI_API_KEY in .env")
        print("3. Run: python main.py")
    else:
        print("\n✗ Setup failed. Check your private key and network connection.")


if __name__ == "__main__":
    main()
