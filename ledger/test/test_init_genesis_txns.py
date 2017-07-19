import os

from ledger.serializers.json_serializer import JsonSerializer
from ledger.test.helper import create_default_ledger
from ledger.util import F
from storage import store_utils


def test_genesis_txn_file_initiator(tempdir, init_genesis_txn_file, genesis_txns):
    # Check that initiator of genesis txns work:
    # It uses a text file with JsonSerializer by default
    genesis_file = os.path.join(tempdir, init_genesis_txn_file)
    assert os.path.exists(genesis_file)
    i = 0
    serializer = JsonSerializer()
    with open(genesis_file) as f:
        for line in store_utils.cleanLines(f.readlines()):
            assert sorted(serializer.deserialize(line)) == sorted(genesis_txns[i])
            i += 1


def test_ledger_with_genesis_txns(ledger_with_genesis, genesis_txns):
    # Check that the transactions are added into the Merkle Tree
    assert ledger_with_genesis.size == len(genesis_txns)
    assert ledger_with_genesis._transactionLog.size == len(genesis_txns)
    assert ledger_with_genesis.getBySeqNo(1)

    for i in range(0, len(genesis_txns) - 1):
        seq_no = i + 1
        assert ledger_with_genesis.getBySeqNo(seq_no)

        expected_txn = genesis_txns[i]
        expected_txn[F.seqNo.name] = seq_no
        assert sorted(expected_txn) == sorted(ledger_with_genesis.getBySeqNo(seq_no))


def test_merkle_tree_for_genesis_txns(ledger_with_genesis, genesis_txns):
    assert ledger_with_genesis.tree.root_hash is not None
    assert ledger_with_genesis.tree.tree_size == len(genesis_txns)


def test_init_twice_with_initiator(tempdir, genesis_txns, init_genesis_txn_file):
    ledger = create_default_ledger(tempdir, init_genesis_txn_file)
    size_before = ledger.size
    txn_size_before = ledger._transactionLog.size
    tree_root_hash_before = ledger.tree.root_hash
    tree_size_before = ledger.tree.tree_size
    root_hash_before = ledger.root_hash

    ledger.stop()
    ledger = create_default_ledger(tempdir, init_genesis_txn_file)

    assert size_before == ledger.size
    assert ledger.size == len(genesis_txns)
    assert txn_size_before == ledger._transactionLog.size
    assert ledger._transactionLog.size == len(genesis_txns)
    assert tree_root_hash_before == ledger.tree.root_hash
    assert tree_size_before == ledger.tree.tree_size
    assert root_hash_before == ledger.root_hash


def test_init_twice_without_initiator(tempdir, genesis_txns, init_genesis_txn_file):
    ledger = create_default_ledger(tempdir, init_genesis_txn_file)
    size_before = ledger.size
    txn_size_before = ledger._transactionLog.size
    tree_root_hash_before = ledger.tree.root_hash
    tree_size_before = ledger.tree.tree_size
    root_hash_before = ledger.root_hash

    ledger.stop()
    ledger = create_default_ledger(tempdir)
    assert size_before == ledger.size
    assert ledger.size == len(genesis_txns)
    assert txn_size_before == ledger._transactionLog.size
    assert ledger._transactionLog.size == len(genesis_txns)
    assert tree_root_hash_before == ledger.tree.root_hash
    assert tree_size_before == ledger.tree.tree_size
    assert root_hash_before == ledger.root_hash