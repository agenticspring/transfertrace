"""Input safety: refuse anything that looks like a private key or seed phrase.

This project is strictly DECODE-ONLY. It never needs secrets, so any
key-like input is rejected loudly instead of being processed.
"""

import re


class SecretInputError(Exception):
    pass


def looks_like_private_key(text):
    """True for 64-hex-char strings, with or without a 0x prefix."""
    t = text.strip()
    if t.lower().startswith("0x"):
        t = t[2:]
    return len(t) == 64 and re.fullmatch(r"[0-9a-fA-F]{64}", t) is not None


def looks_like_seed_phrase(text):
    """True for 12/24 whitespace-separated lowercase words (BIP-39-like)."""
    words = text.strip().split()
    return len(words) in (12, 24) and all(
        re.fullmatch(r"[a-z]{3,12}", w) is not None for w in words)


def is_tx_hash(text):
    """True for a plausible 32-byte tx hash (0x + 64 hex)."""
    t = text.strip()
    return (t.startswith("0x") and len(t) == 66
            and re.fullmatch(r"0[xX][0-9a-fA-F]{64}", t) is not None)
