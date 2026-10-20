"""Token metadata resolution via read-only eth_call.

symbol()  selector 0x95d89b41  -> string or bytes32
decimals() selector 0x313ce567 -> uint8 (as uint256)
name()     selector 0x06fdde03  -> string or bytes32 (optional, best-effort)

All calls are eth_call against public RPC; results cached per (contract).
"""

SYMBOL_SEL = "0x95d89b41"
DECIMALS_SEL = "0x313ce567"
NAME_SEL = "0x06fdde03"

_cache = {}


def decode_abi_string(data):
    """Decode an ABI-encoded string or bytes32 into a Python str.

    Handles both return encodings used in the wild:
      string : offset(32) + length(32) + utf8 bytes
      bytes32: a single 32-byte word, right-padded with zeros
    """
    if not data:
        raise ValueError("empty return data")
    if data.startswith("0x"):
        data = data[2:]
    raw = bytes.fromhex(data)
    if len(raw) < 32:
        raise ValueError("return data shorter than one word")
    if len(raw) == 32:
        # bytes32 form: strip trailing NULs, keep printable ASCII only.
        text = raw.split(b"\x00")[0].decode("ascii", errors="strict")
        if not text or not all(32 <= ord(c) < 127 for c in text):
            raise ValueError("not a printable bytes32 symbol")
        return text
    # string form
    offset = int.from_bytes(raw[0:32], "big")
    length = int.from_bytes(raw[offset:offset + 32], "big")
    blob = raw[offset + 32:offset + 32 + length]
    if len(blob) != length:
        raise ValueError("string tail overruns data")
    return blob.decode("utf-8", errors="strict")


def decode_decimals(data):
    """Decode decimals() return value (uint256) into an int."""
    if not data:
        raise ValueError("empty return data")
    if data.startswith("0x"):
        data = data[2:]
    raw = bytes.fromhex(data)
    if len(raw) != 32:
        raise ValueError("decimals return is not 32 bytes")
    value = int.from_bytes(raw, "big")
    if value > 77:  # sanity: no real token exceeds this
        raise ValueError("implausible decimals value: %d" % value)
    return value


def _eth_call(rpc, contract, call_data):
    return rpc.call("eth_call", [{"to": contract, "data": call_data}, "latest"])


def get_token_meta(rpc, contract):
    """Return (symbol, decimals) for a token contract, with graceful fallbacks.

    Unknown/unreachable metadata -> ("?", 18). Never raises.
    """
    key = contract.lower()
    if key in _cache:
        return _cache[key]
    symbol, decimals = "?", 18
    try:
        sym_raw = _eth_call(rpc, contract, SYMBOL_SEL)
        symbol = decode_abi_string(sym_raw)
    except Exception:
        pass
    try:
        dec_raw = _eth_call(rpc, contract, DECIMALS_SEL)
        decimals = decode_decimals(dec_raw)
    except Exception:
        pass
    _cache[key] = (symbol, decimals)
    return symbol, decimals


def format_amount(value, decimals):
    """Human-readable token amount from raw integer value and decimals."""
    if value is None:
        return "?"
    negative = value < 0
    value = abs(value)
    whole = value // (10 ** decimals)
    frac = value % (10 ** decimals)
    if decimals == 0 or frac == 0:
        text = str(whole)
    else:
        frac_text = str(frac).rjust(decimals, "0").rstrip("0")
        text = "%d.%s" % (whole, frac_text)
    return ("-" if negative else "") + text


def clear_cache():
    _cache.clear()
