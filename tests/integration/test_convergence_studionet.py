import json
import os

import pytest
from gltest import get_contract_factory, get_validator_factory
from gltest.assertions import tx_execution_succeeded


CONTRACT = "SourceWeightedDisputeResolver"
ZERO = "0x0000000000000000000000000000000000000000"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_STUDIONET_GLTEST_NONDET") != "1",
    reason=(
        "StudioNet gltest currently cancels resolve_dispute before validator rounds "
        "for this contract; live CLI StudioNet transactions are documented in README."
    ),
)


ITEMS = [
    {"index": 0, "supports": "CLAIMANT", "reliability": "ACCEPTED", "strength": "HIGH", "reason": "official source supports claimant"},
]


def mock_context(now="2026-07-30T10:00:00Z"):
    validators = get_validator_factory().batch_create_mock_validators(
        count=5,
        mock_llm_response={
            "nondet_exec_prompt": {
                "GenLayer validator resolving source-weighted dispute evidence": json.dumps(
                    {"ok": True, "summary": "repeatable assessment", "items": ITEMS, "safe_error": ""}
                )
            }
        },
    )
    return {"validators": [v.to_dict() for v in validators], "genvm_datetime": now}


def policy_args():
    return [
        "Reserve proof policy",
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


def dispute_args(policy_id):
    return [
        policy_id,
        "Whether Provider Delta had verified reserve coverage for the July reporting window.",
        "Provider Delta had verified reserve coverage.",
        "Provider Delta did not have verified reserve coverage.",
        3600,
        7200,
        ZERO,
    ]


def evidence_args(dispute_id, source, text):
    return [dispute_id, "CLAIMANT", source, text, "convergence evidence"]


def resolve_one(contract, dispute_id):
    assert tx_execution_succeeded(contract.open_dispute(args=dispute_args(1)).transact(transaction_context=mock_context()))
    assert tx_execution_succeeded(contract.submit_evidence(args=evidence_args(dispute_id, "OFFICIAL", "Official registry confirms reserves.")).transact(transaction_context=mock_context()))
    assert tx_execution_succeeded(contract.lock_evidence(args=[dispute_id]).transact(transaction_context=mock_context()))
    assert tx_execution_succeeded(
        contract.resolve_dispute(args=[dispute_id]).transact(
            transaction_context=mock_context(), wait_interval=5000, wait_retries=120
        )
    )
    dispute = json.loads(contract.dispute_of(args=[dispute_id]).call())
    assessment = json.loads(contract.assessment_of(args=[dispute_id]).call())
    return {
        "verdict": dispute["verdict"],
        "claimant_score": dispute["claimant_score"],
        "respondent_score": dispute["respondent_score"],
        "items": assessment["items"],
    }


def test_weighted_assessment_converges_identically(default_account):
    factory = get_contract_factory(CONTRACT)
    contract = factory.deploy(account=default_account, transaction_context=mock_context()).connect(default_account)
    assert tx_execution_succeeded(contract.create_policy(args=policy_args()).transact(transaction_context=mock_context()))
    assert tx_execution_succeeded(
        contract.authorize_source(args=[1, default_account.address, "OFFICIAL"]).transact(transaction_context=mock_context())
    )

    first = resolve_one(contract, 1)
    second = resolve_one(contract, 2)
    assert first == second
