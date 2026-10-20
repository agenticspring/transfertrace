"""Pure-Python Keccak-256 (pre-NIST, as used by Ethereum).

Used only to self-verify the hardcoded event-topic constants in decode.py
against their canonical signatures. stdlib-only, no dependencies.
"""

ROT = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]

RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

MASK64 = 0xFFFFFFFFFFFFFFFF


def _rotl64(x, n):
    n %= 64
    return ((x << n) | (x >> (64 - n))) & MASK64


def _keccak_f1600(state):
    for rnd in range(24):
        # theta
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
             for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl64(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]
        # rho + pi
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl64(state[x + 5 * y], ROT[x][y])
        # chi
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])
        # iota
        state[0] ^= RC[rnd]


def keccak_256(data: bytes) -> bytes:
    """Return Keccak-256 digest of *data* (Ethereum variant, NOT NIST SHA3)."""
    rate = 136  # bytes for 256-bit output
    state = [0] * 25
    off = 0
    n = len(data)
    # absorb complete blocks
    while n - off >= rate:
        for i in range(rate):
            state[i // 8] ^= data[off + i] << (8 * (i % 8))
        _keccak_f1600(state)
        off += rate
    # final block: remaining bytes + pad10*1 with 0x01 domain suffix
    block = bytearray(rate)
    rem = data[off:]
    block[:len(rem)] = rem
    block[len(rem)] = 0x01
    block[-1] |= 0x80
    for i in range(rate):
        state[i // 8] ^= block[i] << (8 * (i % 8))
    _keccak_f1600(state)
    out = bytearray()
    for word in state[:4]:
        out += word.to_bytes(8, "little")
    return bytes(out)
