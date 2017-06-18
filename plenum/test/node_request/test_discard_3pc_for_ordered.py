from plenum.test.delayers import delay_3pc_messages
from plenum.test.helper import sendReqsToNodesAndVerifySuffReplies, \
    countDiscarded
from plenum.test.node_catchup.helper import waitNodeDataEquality
from plenum.test.node_request.node_request_helper import \
    chk_commits_prepares_recvd
from plenum.test.pool_transactions.conftest import looper, clientAndWallet1, \
    client1, wallet1, client1Connected
from plenum.test.test_node import getNonPrimaryReplicas
from stp_core.loop.eventually import eventually


def test_discard_3PC_messages_for_already_ordered(looper, txnPoolNodeSet,
                                                  client1, wallet1,
                                                  client1Connected):
    """
    Nodes discard any 3PC messages for already ordered 3PC keys
    (view_no, pp_seq_no). Delay all 3PC messages to a node so it cannot respond
    to them unless the other nodes order them, now when the slow node will get
    them it will respond but other nodes will not process them and discard them
    """
    slow_node = [r.node for r in getNonPrimaryReplicas(txnPoolNodeSet, 0)][-1]
    other_nodes = [n for n in txnPoolNodeSet if n != slow_node]
    delay = 20
    delay_3pc_messages([slow_node], 0, delay)
    delay_3pc_messages([slow_node], 1, delay)

    sent_batches = 3
    for i in range(sent_batches):
        sendReqsToNodesAndVerifySuffReplies(looper, wallet1, client1, 2)

    def chk(node, inst_id, p_count, c_count):
        # A node will still record PREPRAREs even if more than 2f, till the
        # request is not ordered
        assert len(node.replicas[inst_id].prepares) >= p_count
        assert len(node.replicas[inst_id].commits) == c_count

    def count_discarded(inst_id, count):
        for node in other_nodes:
            assert countDiscarded(node.replicas[inst_id],
                                  'already ordered 3 phase message') == count

    # `slow_node` did not receive any PREPAREs or COMMITs
    chk(slow_node, 0, 0, 0)

    # `other_nodes` have not discarded any 3PC message
    count_discarded(0, 0)

    # `other_nodes` have not recorded any PREPAREs or COMMITs from `slow_node`
    chk_commits_prepares_recvd(0, other_nodes, slow_node)

    slow_node.reset_delays_and_process_delayeds()
    waitNodeDataEquality(looper, slow_node, *other_nodes)

    # `slow_node` did receive correct number of PREPAREs and COMMITs
    looper.run(eventually(chk, slow_node, 0, sent_batches-1, sent_batches,
                          retryWait=1))

    # `other_nodes` have not recorded any PREPAREs or COMMITs from `slow_node`
    chk_commits_prepares_recvd(0, other_nodes, slow_node)

    # `other_nodes` have discarded PREPAREs and COMMITs all batches
    count_discarded(0, 2*sent_batches)