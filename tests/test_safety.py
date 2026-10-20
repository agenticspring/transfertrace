import unittest

from transfertrace.safety import (looks_like_private_key, looks_like_seed_phrase,
                                  is_tx_hash)
from transfertrace.cli import validate_txhash
from transfertrace.safety import SecretInputError


class TestSafety(unittest.TestCase):
    def test_private_key_hex_refused(self):
        self.assertTrue(looks_like_private_key("ab" * 32))
        self.assertTrue(looks_like_private_key("0x" + "ab" * 32))

    def test_tx_hash_is_recognised(self):
        self.assertTrue(is_tx_hash("0x" + "ab" * 32))
        self.assertFalse(is_tx_hash("ab" * 32))  # missing prefix: not a hash

    def test_seed_phrase_refused(self):
        words12 = "abandon " * 11 + "about"
        self.assertTrue(looks_like_seed_phrase(words12.strip()))
        self.assertTrue(looks_like_seed_phrase(("word " * 23 + "word").strip()))

    def test_normal_text_is_fine(self):
        self.assertFalse(looks_like_seed_phrase("hello world"))
        self.assertFalse(looks_like_private_key("0x1234"))

    def test_validate_txhash_accepts_good(self):
        validate_txhash("0x" + "ab" * 32)  # must not raise

    def test_validate_txhash_refuses_seed_phrase(self):
        with self.assertRaises(SecretInputError):
            validate_txhash("abandon " * 11 + "about")

    def test_validate_txhash_refuses_bare_key_hex(self):
        with self.assertRaises(SecretInputError):
            validate_txhash("ab" * 32)

    def test_validate_txhash_refuses_garbage(self):
        with self.assertRaises(SecretInputError):
            validate_txhash("not-a-hash")


if __name__ == "__main__":
    unittest.main()
