# transfertrace

**Decode any Ethereum transaction receipt into a human-readable token flow.**

> 🔒 **DECODE-ONLY.** transfertrace reads public JSON-RPC endpoints. It never
> signs transactions, never broadcasts anything, and never handles private
> keys or seed phrases — key-like input is refused with a clear error.

Given a transaction hash, transfertrace fetches its receipt via
`eth_getTransactionReceipt` from a public RPC endpoint, decodes every token
movement in the logs, resolves token metadata (`symbol()`, `decimals()`) via
`eth_call`, and prints a readable flow: which tokens moved from whom to whom,
in what amounts.

## Features

- Decodes **ERC-20** `Transfer`, **ERC-721** `Transfer` (all-indexed form),
  **ERC-1155** `TransferSingle` / `TransferBatch`, and **WETH9**
  `Deposit` / `Withdrawal` events.
- Event topics are **computed at runtime from canonical signatures** with a
  pure-Python Keccak-256, self-verified against known vectors — no magic
  constants to drift.
- Token metadata via read-only `eth_call`; handles both `string` and
  `bytes32` symbol encodings; graceful fallbacks (`?` symbol, 18 decimals)
  when a contract doesn't implement the metadata interface.
- Full `0x` addresses in all output (no truncation).
- Key-like input refused loudly: bare 64-hex strings (indistinguishable from
  a private key) and 12/24-word seed-phrase-like strings → exit code 2.
- **Zero dependencies** — Python 3.9+ stdlib only (`urllib`, `argparse`,
  `json`, `re`).

## Installation

```bash
git clone https://github.com/agenticspring/transfertrace
cd transfertrace
python3 -m unittest discover -s tests -p 'test_*.py'   # 33 tests, all green
```

No `pip install` needed. Requires Python 3.9+.

## Usage

```bash
python3 -m transfertrace.cli 0x<txhash> [--rpc URL] [--json]
```

Exit codes: `0` success · `1` operational error (RPC failure, tx not found) ·
`2` usage/safety error (bad hash, key-like input refused).

### Example

```
$ python3 -m transfertrace.cli 0xabababababababababababababababababababababababababababababababab --rpc http://127.0.0.1:PORT
transfertrace 1.0.0 — DECODE-ONLY: reads public RPC, never signs, never broadcasts, never touches keys.

tx      : 0xabababababababababababababababababababababababababababababababab
sender  : 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
to      : 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
block   : 0x1234
status  : SUCCESS

== USDC  (0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48) ==
  [ERC20] 0xd8da6bf26964af9d7eed9e03e53415d37aa96045 -> 0x000000000000000000000000000000000000dead : 1.5 USDC

== ?  (0x495f947276749ce646f68ac8c24842054a7fe5e) ==
  [ERC1155] 0xd8da6bf26964af9d7eed9e03e53415d37aa96045 -> 0x000000000000000000000000000000000000dead : 0.000000000000000003 x tokenId 7

2 movement(s) decoded.
```

(The example above is the project's own smoke-test fixture, run against a
local fake JSON-RPC server.)

JSON mode for scripting:

```bash
python3 -m transfertrace.cli 0x<txhash> --json | jq .tokens
```

### Configuration

| Flag | Default | Description |
|---|---|---|
| `--rpc URL` | `https://ethereum.publicnode.com` | Any Ethereum JSON-RPC endpoint |
| `--json` | off | Machine-readable output |

No API keys, no `.env` file — the endpoint is just a CLI flag.

## Limitations

- **Decode-only by design**: it cannot sign, broadcast, or build transactions.
- **No prices**: amounts are shown in token units, never USD.
- Only logs in the *receipt* are decoded — internal ETH value transfers
  (call traces) are out of scope.
- Tokens without `symbol()`/`decimals()` show `?` and assume 18 decimals.
- Needs a reachable JSON-RPC endpoint; public endpoints may rate-limit.

## License

MIT — see [LICENSE](LICENSE).
