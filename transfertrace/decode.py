"""Decode Ethereum receipt logs into structured token movements.

Supported events (topic0 matched by value):
  - ERC-20 / ERC-721  Transfer(address,address,uint256)
  - ERC-1155          TransferSingle(address,address,address,uint256,uint256)
  - ERC-1155          TransferBatch(address,address,address,uint256[],uint256[])
  - WETH9             Deposit(address)
  - WETH9             Withdrawal(address,uint256)

Topic constants are self-verified at import time against keccak256 of the
canonical signatures (see transfertrace.keccak).
"""

from .keccak import keccak_256

TRANSFER_SIG = "Transfer(address,address,uint256)"
TRANSFER_SINGLE_SIG = "TransferSingle(address,address,address,uint256,uint256)"
TRANSFER_BATCH_SIG = "TransferBatch(address,address,address,uint256[],uint256[])"
DEPOSIT_SIG = "Deposit(address)"
WITHDRAWAL_SIG = "Withdrawal(address,uint256)"

TOPIC_TRANSFER = keccak_256(TRANSFER_SIG.encode()).hex()
TOPIC_TRANSFER_SINGLE = keccak_256(TRANSFER_SINGLE_SIG.encode()).hex()
TOPIC_TRANSFER_BATCH = keccak_256(TRANSFER_BATCH_SIG.encode()).hex()
TOPIC_DEPOSIT = keccak_256(DEPOSIT_SIG.encode()).hex()
TOPIC_WITHDRAWAL = keccak_256(WITHDRAWAL_SIG.encode()).hex()

# Sanity pins: the ERC-20 Transfer topic is one of the most widely known
# constants in Ethereum. If our Keccak is broken, this fails loudly.
assert TOPIC_TRANSFER == (
    "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
), "keccak-256 self-check failed"


def _topic_word(topic):
    """Return topic hex string without 0x prefix, lowercased."""
    t = topic.lower()
    if t.startswith("0x"):
        t = t[2:]
    return t


def topic_to_address(topic):
    """Extract an address from an indexed topic (last 20 bytes of 32-byte word)."""
    word = _topic_word(topic)
    if len(word) != 64:
        raise ValueError("indexed topic is not a 32-byte word: %r" % topic)
    return "0x" + word[-40:]


def _decode_uint256_array(data, offset_words):
    """Decode a uint256[] at the given word offset inside ABI head+tail data."""
    length = int.from_bytes(data[offset_words * 32:offset_words * 32 + 32], "big")
    start = offset_words * 32 + 32
    if start + length * 32 > len(data):
        raise ValueError("uint256[] tail overruns data")
    return [
        int.from_bytes(data[start + i * 32:start + (i + 1) * 32], "big")
        for i in range(length)
    ]


def decode_log(log):
    """Decode one receipt log dict into a list of movement dicts.

    Returns a (possibly empty) list; logs that are not recognised token
    movements return []. Each movement dict:
        {standard, contract, from, to, token_id, value}
    where standard is one of 'ERC20', 'ERC721', 'ERC1155', 'WETH'.
    """
    topics = log.get("topics") or []
    if not topics:
        return []
    t0 = _topic_word(topics[0])
    contract = log.get("address", "")
    raw = log.get("data", "0x")
    data = bytes.fromhex(_topic_word(raw)) if isinstance(raw, str) else b""

    def movement(standard, frm, to, value, token_id=None):
        return {
            "standard": standard,
            "contract": contract.lower(),
            "from": frm.lower(),
            "to": to.lower(),
            "token_id": token_id,
            "value": value,
        }

    if t0 == TOPIC_TRANSFER:
        # ERC-20 and ERC-721 share the Transfer signature; disambiguate by
        # shape: ERC-20 has 3 topics + 32-byte value in data;
        # ERC-721 indexes all three params (4 topics) with empty data.
        if len(topics) == 3 and len(data) == 32:
            return [movement("ERC20",
                             topic_to_address(topics[1]), topic_to_address(topics[2]),
                             int.from_bytes(data, "big"))]
        if len(topics) == 4 and len(data) == 0:
            token_id = int.from_bytes(bytes.fromhex(_topic_word(topics[3])), "big")
            return [movement("ERC721",
                             topic_to_address(topics[1]), topic_to_address(topics[2]),
                             1, token_id)]
        return []

    if t0 == TOPIC_TRANSFER_SINGLE:
        if len(topics) != 4 or len(data) != 64:
            return []
        token_id = int.from_bytes(data[0:32], "big")
        value = int.from_bytes(data[32:64], "big")
        return [movement("ERC1155",
                         topic_to_address(topics[2]), topic_to_address(topics[3]),
                         value, token_id)]

    if t0 == TOPIC_TRANSFER_BATCH:
        if len(topics) != 4 or len(data) < 128:
            return []
        off_ids = int.from_bytes(data[0:32], "big") // 32
        off_vals = int.from_bytes(data[32:64], "big") // 32
        ids = _decode_uint256_array(data, off_ids)
        vals = _decode_uint256_array(data, off_vals)
        if len(ids) != len(vals):
            return []
        frm = topic_to_address(topics[2])
        to = topic_to_address(topics[3])
        return [movement("ERC1155", frm, to, v, tid)
                for tid, v in zip(ids, vals)]

    if t0 == TOPIC_DEPOSIT:
        # WETH9 Deposit(address dst): data empty, dst indexed in topic1.
        if len(topics) != 2 or len(data) != 0:
            return []
        dst = topic_to_address(topics[1])
        return [movement("WETH", contract, dst, None)]

    if t0 == TOPIC_WITHDRAWAL:
        # WETH9 Withdrawal(address src, uint256 wad): data = wad.
        if len(topics) != 2 or len(data) != 32:
            return []
        src = topic_to_address(topics[1])
        return [movement("WETH", src, contract,
                         int.from_bytes(data, "big"))]

    return []


def decode_receipt_logs(logs):
    """Decode every log of a receipt; return the flat list of movements."""
    moves = []
    for log in logs or []:
        try:
            moves.extend(decode_log(log))
        except (ValueError, IndexError):
            # Malformed log: skip, never crash the whole receipt.
            continue
    return moves
