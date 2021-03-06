import types

from plenum.common.constants import PREPREPARE
from plenum.common.messages.node_messages import MessageRep
from plenum.common.types import f
from plenum.test.delayers import ppDelay
from plenum.test.helper import send_reqs_batches_and_get_suff_replies
from plenum.test.node_catchup.helper import waitNodeDataEquality
from plenum.test.node_request.message_request.helper import split_nodes
from plenum.test.spy_helpers import get_count
from stp_core.loop.eventually import eventually


def test_handle_delayed_preprepares(looper, txnPoolNodeSet, client1,
                                    wallet1, client1Connected, teardown):
    """
    Make a node send PREPREPARE again after the slow node has ordered
    """
    slow_node, other_nodes, primary_node, other_non_primary_nodes = \
        split_nodes(txnPoolNodeSet)
    # This node will send PRE-PREPARE again
    confused_node = other_non_primary_nodes[0]
    orig_method = confused_node._serve_preprepare_request

    last_pp = None

    def patched_method(self, msg):
        nonlocal last_pp
        last_pp = orig_method(msg)
        return last_pp

    confused_node.req_handlers[PREPREPARE] = types.MethodType(patched_method,
                                                               confused_node)

    # Delay PRE-PREPAREs by large amount simulating loss
    slow_node.nodeIbStasher.delay(ppDelay(300, 0))

    send_reqs_batches_and_get_suff_replies(looper, wallet1, client1, 10, 5)
    waitNodeDataEquality(looper, slow_node, *other_nodes)

    slow_master_replica = slow_node.master_replica
    count_pr_req = get_count(slow_master_replica,
                             slow_master_replica.process_requested_pre_prepare)

    count_pr_tpc = get_count(slow_master_replica,
                             slow_master_replica.processThreePhaseMsg)

    confused_node.sendToNodes(MessageRep(**{
        f.MSG_TYPE.nm: PREPREPARE,
        f.PARAMS.nm: {
            f.INST_ID.nm: last_pp.instId,
            f.VIEW_NO.nm: last_pp.viewNo,
            f.PP_SEQ_NO.nm: last_pp.ppSeqNo
        },
        f.MSG.nm: last_pp
    }), names=[slow_node.name, ])

    def chk():
        # `process_requested_pre_prepare` is called but
        # `processThreePhaseMsg` is not called
        assert get_count(slow_master_replica,
                         slow_master_replica.process_requested_pre_prepare) > count_pr_req
        assert get_count(slow_master_replica,
                  slow_master_replica.processThreePhaseMsg) == count_pr_tpc

    looper.run(eventually(chk, retryWait=1))
