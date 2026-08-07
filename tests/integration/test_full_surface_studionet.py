import json
import os

import pytest
from gltest import get_contract_factory, get_validator_factory
from gltest.assertions import tx_execution_failed, tx_execution_succeeded


CONTRACT = "SourceWeightedDisputeResolver"
ZERO = "0x0000000000000000000000000000000000000000"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_STUDIONET_GLTEST_NONDET") != "1",
    reason=(
        "StudioNet gltest currently cancels resolve_dispute before validator rounds "
        "for this contract; live CLI StudioNet transactions are documented in README."
    ),
)


def mock_context(now="2026-07-30T10:00:00Z", items=None):
    if items is None:
        items = [
            {"index": 0, "supports": "CLAIMANT", "reliability": "ACCEPTED", "strength": "HIGH", "reason": "official source supports claimant"},
        ]
    validators = get_validator_factory().batch_create_mock_validators(
        count=5,
        mock_llm_response={
            "nondet_exec_prompt": {
                "GenLayer validator resolving source-weighted dispute evidence": json.dumps(
                    {"ok": True, "summary": "mocked StudioNet evidence assessment", "items": items, "safe_error": ""}
                )
            }
        },
    )
    return {"validators": [v.to_dict() for v in validators], "genvm_datetime": now}


def policy_args(name="Reserve proof policy"):
    return [
        name,
        "Official regulator and audited statements outrank party claims. News can corroborate but not decide alone.",
        50,
        20,
        50,
        45,
        35,
        25,
        18,
        10,
        5,
    ]


def dispute_args(policy_id, callback=ZERO):
    return [
        policy_id,
        "Whether Provider Gamma had verified reserve coverage for the July reporting window.",
        "Provider Gamma had verified reserve coverage.",
        "Provider Gamma did not have verified reserve coverage.",
        3600,
        7200,
        callback,
    ]


def evidence_args(dispute_id, side="CLAIMANT", source="OFFICIAL", text="Official registry says Provider Gamma reserves were verified."):
    return [dispute_id, side, source, text, "StudioNet integration evidence"]


def test_full_surface_on_studionet(default_account):
    factory = get_contract_factory(CONTRACT)
    contract = factory.deploy(account=default_account, transaction_context=mock_context()).connect(default_account)

    policy_tx = contract.create_policy(args=policy_args()).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(policy_tx)
    open_tx = contract.open_dispute(args=dispute_args(1)).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(open_tx)
    authorize_tx = contract.authorize_source(args=[1, default_account.address, "OFFICIAL"]).transact(
        transaction_context=mock_context()
    )
    assert tx_execution_succeeded(authorize_tx)
    evidence0_tx = contract.submit_evidence(args=evidence_args(1, "CLAIMANT", "OFFICIAL")).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(evidence0_tx)
    lock_tx = contract.lock_evidence(args=[1]).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(lock_tx)
    resolve_tx = contract.resolve_dispute(args=[1]).transact(
        transaction_context=mock_context(), wait_interval=5000, wait_retries=120
    )
    if not tx_execution_succeeded(resolve_tx):
        print(json.dumps(resolve_tx, default=str)[:6000])
    assert tx_execution_succeeded(resolve_tx)
    callback_tx = contract.send_callback(args=[1]).transact(transaction_context=mock_context())
    assert tx_execution_failed(callback_tx)
    archive_tx = contract.archive_dispute(args=[1]).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(archive_tx)

    inactive_policy_tx = contract.create_policy(args=policy_args("Temporary policy")).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(inactive_policy_tx)
    deactivate_tx = contract.deactivate_policy(args=[2]).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(deactivate_tx)
    inactive_open_tx = contract.open_dispute(args=dispute_args(2)).transact(transaction_context=mock_context())
    assert tx_execution_failed(inactive_open_tx)

    timeout_open_tx = contract.open_dispute(args=dispute_args(1)).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(timeout_open_tx)
    timeout_evidence_tx = contract.submit_evidence(args=evidence_args(2)).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(timeout_evidence_tx)
    timeout_lock_tx = contract.lock_evidence(args=[2]).transact(transaction_context=mock_context())
    assert tx_execution_succeeded(timeout_lock_tx)
    bad_source_tx = contract.submit_evidence(args=evidence_args(2, "CLAIMANT", "BLOG")).transact(transaction_context=mock_context())
    assert tx_execution_failed(bad_source_tx)
    timeout_tx = contract.timeout_dispute(args=[2]).transact(transaction_context=mock_context(now="2026-07-30T12:00:01Z"))
    assert tx_execution_succeeded(timeout_tx)

    assert json.loads(contract.policy_of(args=[1]).call())["active"] is True
    assert contract.dispute_status(args=[1]).call() == "ARCHIVED"
    assert contract.dispute_verdict(args=[1]).call() == "CLAIMANT"
    assert json.loads(contract.dispute_of(args=[1]).call())["claimant_score"] == 50
    assert json.loads(contract.evidence_of(args=[1, 0]).call())["source_class"] == "OFFICIAL"
    assert json.loads(contract.assessment_of(args=[1]).call())["items"][0]["supports"] == "CLAIMANT"
    stats = json.loads(contract.stats(args=[]).call())
    assert int(stats["next_policy_id"]) == 3
    assert int(stats["next_dispute_id"]) == 3
