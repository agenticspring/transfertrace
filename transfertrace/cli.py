"""transfertrace CLI: decode any Ethereum tx receipt into a token flow.

DECODE-ONLY. This tool never signs, never broadcasts, and never touches
private keys or seed phrases. It only reads from public JSON-RPC endpoints.
"""

import argparse
import json
import sys

from . import __version__, BANNER
from .safety import (is_tx_hash, looks_like_private_key,
                     looks_like_seed_phrase, SecretInputError)
from .rpc import RpcClient, RpcError
from .decode import decode_receipt_logs
from .metadata import get_token_meta, format_amount

DEFAULT_RPC = "https://ethereum.publicnode.com"

EXIT_OK = 0
EXIT_OPERATIONAL = 1   # RPC failure, tx not found, ...
EXIT_USAGE = 2         # bad arguments, key-like input refused


def build_parser():
    p = argparse.ArgumentParser(
        prog="transfertrace",
        description="Decode an Ethereum transaction receipt into a "
                    "human-readable token flow. READ-ONLY: never signs or "
                    "broadcasts; never handles private keys or seed phrases.")
    p.add_argument("txhash", help="0x-prefixed 64-hex transaction hash")
    p.add_argument("--rpc", default=DEFAULT_RPC,
                   help="JSON-RPC endpoint (default: %(default)s)")
    p.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON instead of text")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    return p


def validate_txhash(txhash):
    # Key-like input is refused loudly (a bare 64-hex string is
    # indistinguishable from a private key without the 0x tx-hash prefix).
    if looks_like_seed_phrase(txhash):
        raise SecretInputError(
            "refusing input: it looks like a seed phrase (12/24 words). "
            "transfertrace is decode-only and never handles seed phrases.")
    if not is_tx_hash(txhash):
        if looks_like_private_key(txhash):
            raise SecretInputError(
                "refusing input: 64 hex chars without the 0x prefix is "
                "indistinguishable from a private key. Pass the transaction "
                "hash with its 0x prefix.")
        raise SecretInputError(
            "invalid transaction hash %r: expected 0x followed by 64 hex "
            "characters." % txhash)


def fetch_trace(rpc, txhash):
    tx, receipt = rpc.batch([
        ("eth_getTransactionByHash", [txhash]),
        ("eth_getTransactionReceipt", [txhash]),
    ])
    if tx is None:
        raise RpcError("transaction not found: %s" % txhash)
    if receipt is None:
        raise RpcError("no receipt yet for transaction (still pending?): %s"
                       % txhash)
    return tx, receipt


def build_flow(rpc, txhash):
    tx, receipt = fetch_trace(rpc, txhash)
    movements = decode_receipt_logs(receipt.get("logs") or [])
    by_token = {}
    for m in movements:
        symbol, decimals = get_token_meta(rpc, m["contract"])
        key = m["contract"]
        entry = by_token.setdefault(key, {
            "contract": key, "symbol": symbol, "decimals": decimals,
            "transfers": []})
        entry["transfers"].append({
            "standard": m["standard"],
            "from": m["from"],
            "to": m["to"],
            "token_id": m["token_id"],
            "value_raw": None if m["value"] is None else str(m["value"]),
            "amount": ("?" if m["value"] is None
                       else format_amount(m["value"], decimals)),
        })
    return {
        "tx_hash": txhash,
        "status": receipt.get("status"),
        "sender": tx.get("from"),
        "to": tx.get("to"),
        "block_number": receipt.get("blockNumber"),
        "tokens": list(by_token.values()),
        "movement_count": len(movements),
    }


def render_text(flow):
    lines = [BANNER, ""]
    lines.append("tx      : %s" % flow["tx_hash"])
    lines.append("sender  : %s" % (flow["sender"] or "?"))
    lines.append("to      : %s" % (flow["to"] or "? (contract creation)"))
    lines.append("block   : %s" % (flow["block_number"] or "?"))
    status = flow["status"]
    lines.append("status  : %s" % ("SUCCESS" if status in ("0x1", 1, "1")
                                   else "FAILED" if status in ("0x0", 0, "0")
                                   else "?"))
    lines.append("")
    if not flow["tokens"]:
        lines.append("No ERC-20 / ERC-721 / ERC-1155 / WETH token movements "
                     "decoded from this receipt's logs.")
        return "\n".join(lines)
    for tok in flow["tokens"]:
        lines.append("== %s  (%s) ==" % (tok["symbol"], tok["contract"]))
        for t in tok["transfers"]:
            if t["standard"] == "ERC721":
                detail = "tokenId %s" % t["token_id"]
            elif t["standard"] == "ERC1155":
                detail = "%s x tokenId %s" % (t["amount"], t["token_id"])
            else:
                detail = "%s %s" % (t["amount"], tok["symbol"])
            lines.append("  [%s] %s -> %s : %s"
                         % (t["standard"], t["from"], t["to"], detail))
        lines.append("")
    lines.append("%d movement(s) decoded." % flow["movement_count"])
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        validate_txhash(args.txhash)
    except SecretInputError as e:
        print("error: %s" % e, file=sys.stderr)
        return EXIT_USAGE
    rpc = RpcClient(args.rpc)
    try:
        flow = build_flow(rpc, args.txhash)
    except RpcError as e:
        print("error: %s" % e, file=sys.stderr)
        return EXIT_OPERATIONAL
    if args.json:
        print(json.dumps(flow, indent=2))
    else:
        sys.stdout.write(render_text(flow))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
