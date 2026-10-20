import unittest

import fixtures
from transfertrace.metadata import (decode_abi_string, decode_decimals,
                                    format_amount)


class TestMetadataDecode(unittest.TestCase):
    def test_abi_string_form(self):
        self.assertEqual(decode_abi_string(fixtures.SYMBOL_USDC), "USDC")

    def test_bytes32_form(self):
        self.assertEqual(decode_abi_string(fixtures.SYMBOL_MKR), "MKR")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            decode_abi_string("0x")

    def test_decimals(self):
        self.assertEqual(decode_decimals(fixtures.DECIMALS_6), 6)
        self.assertEqual(decode_decimals(fixtures.DECIMALS_18), 18)

    def test_decimals_implausible(self):
        with self.assertRaises(ValueError):
            decode_decimals("0x" + (200).to_bytes(32, "big").hex())

    def test_format_amount(self):
        self.assertEqual(format_amount(1_500_000, 6), "1.5")
        self.assertEqual(format_amount(2_000_000_000_000_000_000, 18), "2")
        self.assertEqual(format_amount(1, 18), "0.000000000000000001")
        self.assertEqual(format_amount(0, 6), "0")
        self.assertEqual(format_amount(42, 0), "42")
        self.assertEqual(format_amount(None, 18), "?")


if __name__ == "__main__":
    unittest.main()
