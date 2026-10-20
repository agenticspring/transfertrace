import unittest

import fixtures
from transfertrace.keccak import keccak_256
from transfertrace.decode import (
    decode_log, decode_receipt_logs, topic_to_address,
    TOPIC_TRANSFER, TOPIC_TRANSFER_SINGLE, TOPIC_TRANSFER_BATCH,
    TOPIC_DEPOSIT, TOPIC_WITHDRAWAL,
)


class TestKeccakSelfVerification(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(
            keccak_256(b"Transfer(address,address,uint256)").hex(), TOPIC_TRANSFER)
        self.assertEqual(
            TOPIC_TRANSFER,
            "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")
        self.assertEqual(
            keccak_256(b"TransferSingle(address,address,address,uint256,uint256)").hex(),
            TOPIC_TRANSFER_SINGLE)
        self.assertEqual(
            keccak_256(b"TransferBatch(address,address,address,uint256[],uint256[])").hex(),
            TOPIC_TRANSFER_BATCH)
        self.assertEqual(
            TOPIC_TRANSFER_BATCH,
            "4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb")
        self.assertEqual(keccak_256(b"Deposit(address)").hex(), TOPIC_DEPOSIT)
        self.assertEqual(keccak_256(b"Withdrawal(address,uint256)").hex(), TOPIC_WITHDRAWAL)


class TestDecodeLog(unittest.TestCase):
    def test_erc20(self):
        moves = decode_log(fixtures.erc20_log())
        self.assertEqual(len(moves), 1)
        m = moves[0]
        self.assertEqual(m["standard"], "ERC20")
        self.assertEqual(m["from"], fixtures.VITALIK.lower())
        self.assertEqual(m["to"], fixtures.BURN.lower())
        self.assertEqual(m["value"], 1_500_000)
        self.assertEqual(m["contract"], fixtures.USDC.lower())

    def test_erc721(self):
        moves = decode_log(fixtures.erc721_log())
        self.assertEqual(len(moves), 1)
        m = moves[0]
        self.assertEqual(m["standard"], "ERC721")
        self.assertEqual(m["token_id"], 123)
        self.assertEqual(m["from"], fixtures.VITALIK.lower())
        self.assertEqual(m["to"], fixtures.BURN.lower())

    def test_ambiguous_three_topic_empty_data_ignored(self):
        # 3 topics + empty data is neither ERC-20 nor ERC-721 -> skip safely.
        log = {"address": fixtures.USDC,
               "topics": [fixtures.T0_TRANSFER, fixtures.topic(fixtures.VITALIK),
                          fixtures.topic(fixtures.BURN)],
               "data": "0x"}
        self.assertEqual(decode_log(log), [])

    def test_erc1155_single(self):
        moves = decode_log(fixtures.erc1155_single_log())
        self.assertEqual(len(moves), 1)
        m = moves[0]
        self.assertEqual(m["standard"], "ERC1155")
        self.assertEqual(m["token_id"], 7)
        self.assertEqual(m["value"], 3)
        self.assertEqual(m["from"], fixtures.VITALIK.lower())
        self.assertEqual(m["to"], fixtures.BURN.lower())

    def test_erc1155_batch(self):
        moves = decode_log(fixtures.erc1155_batch_log())
        self.assertEqual(len(moves), 2)
        self.assertEqual([(m["token_id"], m["value"]) for m in moves],
                         [(5, 10), (9, 20)])
        for m in moves:
            self.assertEqual(m["standard"], "ERC1155")
            self.assertEqual(m["from"], fixtures.VITALIK.lower())
            self.assertEqual(m["to"], fixtures.BURN.lower())

    def test_weth_deposit_withdrawal(self):
        dep = decode_log(fixtures.weth_deposit_log())[0]
        self.assertEqual(dep["standard"], "WETH")
        self.assertEqual(dep["to"], fixtures.VITALIK.lower())
        wd = decode_log(fixtures.weth_withdrawal_log())[0]
        self.assertEqual(wd["standard"], "WETH")
        self.assertEqual(wd["from"], fixtures.VITALIK.lower())
        self.assertEqual(wd["value"], 2_000_000_000_000_000_000)

    def test_unknown_log_ignored(self):
        self.assertEqual(decode_log(fixtures.unknown_log()), [])

    def test_empty_topics_ignored(self):
        self.assertEqual(decode_log({"address": fixtures.USDC, "topics": [], "data": "0x"}), [])

    def test_malformed_skipped_by_receipt_decoder(self):
        logs = [fixtures.erc20_log(), fixtures.malformed_transfer_log(),
                fixtures.unknown_log(), {"topics": ["0xzz"], "data": "0x"}]
        moves = decode_receipt_logs(logs)
        self.assertEqual(len(moves), 1)  # only the good ERC-20 survives

    def test_mixed_receipt(self):
        logs = [fixtures.erc20_log(), fixtures.erc721_log(),
                fixtures.erc1155_single_log(), fixtures.erc1155_batch_log(),
                fixtures.weth_deposit_log(), fixtures.weth_withdrawal_log(),
                fixtures.unknown_log()]
        moves = decode_receipt_logs(logs)
        self.assertEqual(len(moves), 7)

    def test_topic_to_address_bad_word(self):
        with self.assertRaises(ValueError):
            topic_to_address("0x1234")


if __name__ == "__main__":
    unittest.main()
