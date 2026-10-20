"""Synthetic fixtures for transfertrace tests.

All addresses/contracts are well-known public constants (vitalik.eth, the
burn address, USDC, WETH) or purely synthetic. No real user data.
"""

VITALIK = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
BURN = "0x000000000000000000000000000000000000dEaD"
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
MKR = "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2"
NOPMETA = "0x1111111111111111111111111111111111111111"

TXHASH = "0x" + "ab" * 32


def topic(addr):
    """Encode an address as a 32-byte indexed topic."""
    a = addr[2:].lower()
    return "0x" + "00" * 12 + a


def u256(n):
    return "0x" + n.to_bytes(32, "big").hex()


T0_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# Topics are computed by transfertrace.decode from canonical signatures
# (keccak verified against known vectors); import them so fixtures can't drift.
from transfertrace.decode import (TOPIC_TRANSFER_SINGLE, TOPIC_TRANSFER_BATCH,
                                  TOPIC_DEPOSIT, TOPIC_WITHDRAWAL)

T0_SINGLE = "0x" + TOPIC_TRANSFER_SINGLE
T0_BATCH = "0x" + TOPIC_TRANSFER_BATCH
T0_DEPOSIT = "0x" + TOPIC_DEPOSIT
T0_WITHDRAWAL = "0x" + TOPIC_WITHDRAWAL


def erc20_log():
    return {"address": USDC, "topics": [T0_TRANSFER, topic(VITALIK), topic(BURN)],
            "data": u256(1_500_000)}


def erc721_log():
    # ERC-721 Transfer: all three params indexed (4 topics), empty data.
    return {"address": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
            "topics": [T0_TRANSFER, topic(VITALIK), topic(BURN), u256(123)],
            "data": "0x"}


def erc1155_single_log():
    data = u256(7)[2:] + u256(3)[2:]
    return {"address": "0x495f947276749Ce646F68AC8c24842054a7FE5e",
            "topics": [T0_SINGLE, topic(VITALIK), topic(VITALIK), topic(BURN)],
            "data": "0x" + data}


def erc1155_batch_log():
    # ids=[5,9], values=[10,20]
    # head: word0 = byte offset of ids tail (0x40), word1 = byte offset of
    # values tail (0xA0 = 64 head + 96 ids tail)
    ids = u256(2)[2:] + u256(5)[2:] + u256(9)[2:]
    vals = u256(2)[2:] + u256(10)[2:] + u256(20)[2:]
    data = u256(0x40)[2:] + u256(0xA0)[2:] + ids + vals
    return {"address": "0x495f947276749Ce646F68AC8c24842054a7FE5e",
            "topics": [T0_BATCH, topic(VITALIK), topic(VITALIK), topic(BURN)],
            "data": "0x" + data}


def weth_deposit_log():
    return {"address": WETH, "topics": [T0_DEPOSIT, topic(VITALIK)], "data": "0x"}


def weth_withdrawal_log():
    return {"address": WETH, "topics": [T0_WITHDRAWAL, topic(VITALIK)],
            "data": u256(2_000_000_000_000_000_000)}


def unknown_log():
    return {"address": USDC,
            "topics": ["0x" + "11" * 32, topic(VITALIK)], "data": "0x"}


def malformed_transfer_log():
    # Transfer topic but only 2 topics -> must be skipped, not crash.
    return {"address": USDC, "topics": [T0_TRANSFER, topic(VITALIK)],
            "data": u256(1)}


def abi_string(s):
    b = s.encode("utf-8")
    blob = b + b"\x00" * ((32 - len(b) % 32) % 32)
    return "0x" + (32).to_bytes(32, "big").hex() + len(b).to_bytes(32, "big").hex() + blob.hex()


def bytes32_symbol(s):
    b = s.encode("ascii")
    return "0x" + (b + b"\x00" * (32 - len(b))).hex()


SYMBOL_USDC = abi_string("USDC")
SYMBOL_MKR = bytes32_symbol("MKR")
DECIMALS_6 = u256(6)
DECIMALS_18 = u256(18)
