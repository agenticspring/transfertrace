"""transfertrace — read-only Ethereum transaction token-flow decoder."""

__version__ = "1.0.0"

BANNER = ("transfertrace %s — DECODE-ONLY: reads public RPC, never signs, "
          "never broadcasts, never touches keys." % __version__)

from .decode import decode_log, decode_receipt_logs  # noqa: E402,F401
