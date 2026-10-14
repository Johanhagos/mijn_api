"""On-chain verification of invoice payments in an ERC-20 token (APIUSD on Sepolia by default).

A payment counts only when the transaction is mined successfully, has the required number
of confirmations, and contains a Transfer of the configured token to the configured wallet.
Nothing here trusts amounts or statuses sent by the client.
"""
import os
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

import requests

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


class Config:
    def __init__(self):
        self.chain_id = int(os.getenv("PAYMENT_CHAIN_ID", "11155111"))  # Sepolia
        self.chain_name = os.getenv("PAYMENT_CHAIN_NAME", "Sepolia")
        # Several public RPCs, tried in order: some prune receipts or rate-limit.
        self.rpc_urls = [u.strip() for u in os.getenv(
            "PAYMENT_RPC_URLS",
            "https://sepolia.drpc.org,https://sepolia.gateway.tenderly.co,https://ethereum-sepolia-rpc.publicnode.com",
        ).split(",") if u.strip()]
        self.token_address = os.getenv("PAYMENT_TOKEN_ADDRESS", "0x354CBbF9aCcbf79B223ef153f2fb91C2c0AeD521")
        self.token_symbol = os.getenv("PAYMENT_TOKEN_SYMBOL", "APIUSD")
        self.token_decimals = int(os.getenv("PAYMENT_TOKEN_DECIMALS", "6"))
        self.wallet_address = os.getenv("PAYMENT_WALLET_ADDRESS", "")
        self.confirmations = int(os.getenv("PAYMENT_CONFIRMATIONS", "3"))
        self.explorer_tx_url = os.getenv("PAYMENT_EXPLORER_TX_URL", "https://sepolia.etherscan.io/tx/")

    @property
    def enabled(self) -> bool:
        return bool(ADDRESS_RE.match(self.wallet_address)) and bool(ADDRESS_RE.match(self.token_address))

    @property
    def chain_key(self) -> str:
        return f"eip155:{self.chain_id}"


def config() -> Config:
    return Config()


def to_units(amount, decimals: int) -> int:
    """Invoice amount (EUR, 1:1 with the token) -> token base units, without float rounding."""
    q = Decimal(str(amount or 0)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return int(q.scaleb(decimals))


def from_units(units: int, decimals: int) -> str:
    return format(Decimal(units).scaleb(-decimals), f".{decimals}f")


def _rpc_single(url: str, method: str, params: list):
    resp = requests.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=15)
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(f"RPC error: {body['error']}")
    return body.get("result")


def rpc_call(cfg: Config, method: str, params: list):
    """Ask each RPC in turn. An empty result (e.g. a receipt a node has pruned) falls through
    to the next provider. Returns None only if some provider answered and none had a result;
    raises if no provider could be reached at all."""
    answered, last_error = False, None
    for url in cfg.rpc_urls:
        try:
            result = _rpc_single(url, method, params)
        except Exception as exc:
            last_error = exc
            continue
        answered = True
        if result is not None:
            return result
    if not answered:
        raise RuntimeError(f"No payment RPC reachable: {last_error}")
    return None


def _topic_address(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def verify_transfer(cfg: Config, tx_hash: str, rpc=None) -> dict:
    """Check a transaction on-chain.

    Returns a dict with `state`:
      - "pending":   not mined yet, or fewer confirmations than required
      - "confirmed": mined, successful, enough confirmations; `units` sent to the wallet
      - "failed":    mined but reverted
      - "invalid":   mined but contains no transfer of the token to the wallet
    """
    rpc = rpc or (lambda method, params: rpc_call(cfg, method, params))
    receipt = rpc("eth_getTransactionReceipt", [tx_hash])
    if not receipt:
        return {"state": "pending", "confirmations": 0, "units": 0}
    if int(receipt.get("status", "0x0"), 16) != 1:
        return {"state": "failed", "reason": "Transaction failed on the blockchain"}

    token = cfg.token_address.lower()
    wallet = cfg.wallet_address.lower()
    units, payer = 0, None
    for log in receipt.get("logs", []):
        topics = log.get("topics") or []
        if (str(log.get("address", "")).lower() == token and len(topics) == 3
                and topics[0].lower() == TRANSFER_TOPIC and _topic_address(topics[2]) == wallet):
            units += int(log.get("data") or "0x0", 16)
            payer = _topic_address(topics[1])
    if units == 0:
        return {"state": "invalid",
                "reason": f"Transaction contains no {cfg.token_symbol} transfer to the payment address"}

    block_number = int(receipt["blockNumber"], 16)
    latest = int(rpc("eth_blockNumber", []), 16)
    confirmations = latest - block_number + 1
    block = rpc("eth_getBlockByNumber", [receipt["blockNumber"], False]) or {}
    timestamp = int(block.get("timestamp", "0x0"), 16)
    result = {"units": units, "payer": payer, "block_number": block_number,
              "confirmations": confirmations, "timestamp": timestamp}
    result["state"] = "confirmed" if confirmations >= cfg.confirmations else "pending"
    return result


def normalise_tx_hash(tx_hash: Optional[str]) -> Optional[str]:
    if not tx_hash or not TX_HASH_RE.match(tx_hash.strip()):
        return None
    return tx_hash.strip().lower()
