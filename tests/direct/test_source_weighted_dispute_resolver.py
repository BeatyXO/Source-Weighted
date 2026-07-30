import json

from conftest import warp_to


CONTRACT = "contracts/source_weighted_dispute_resolver.py"
ZERO = "0x0000000000000000000000000000000000000000"


def deploy(direct_deploy, direct_vm):
    contract = direct_deploy(CONTRACT)
    direct_vm.check_pickling = True
    warp_to(direct_vm, "2026-07-30T10:00:00Z")
    return contract


def create_policy(contract, direct_vm, sender):
    direct_vm.sender = sender
    return contract.create_policy(
        "Reserve proof policy",
        "Official regulator and audited statements outrank party claims. News can corroborate but not decide alone.",
        70,
        20,
        50,
        45,
        35,
        25,
        18,
        10,
        5,
    )


def open_default(contract, direct_vm, sender, policy_id=1, callback=ZERO):
    direct_vm.sender = sender
    return contract.open_dispute(
        policy_id,
        "Whether Provider Gamma had verified reserve coverage for the July reporting window.",
        "Provider Gamma had verified reserve coverage.",
        "Provider Gamma did not have verified reserve coverage.",
        3600,
        7200,
        callback,
    )


def submit(contract, direct_vm, sender, dispute_id, side, source_class, body="evidence text"):
    direct_vm.sender = sender
    contract.submit_evidence(dispute_id, side, source_class, body, "direct test evidence")


def lock(contract, direct_vm, dispute_id, sender):
    direct_vm.sender = sender
    contract.lock_evidence(dispute_id)


def assessment(items, ok=True, summary="mocked assessment"):
    return json.dumps({"ok": ok, "summary": summary, "items": items, "safe_error": ""})


def item(index, supports, reliability="ACCEPTED", strength="HIGH"):
    return {
        "index": index,
        "supports": supports,
        "reliability": reliability,
        "strength": strength,
        "reason": "classified evidence",
    }


def mock_assessment(direct_vm, items, ok=True):
    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r".*GenLayer validator resolving source-weighted dispute evidence.*",
        assessment(items, ok),
    )


def dispute(contract, dispute_id):
    return json.loads(contract.dispute_of(dispute_id))


def policy(contract, policy_id):
    return json.loads(contract.policy_of(policy_id))


def test_create_policy_records_weights_and_creator(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    policy_id = create_policy(contract, direct_vm, direct_alice)
    rec = policy(contract, policy_id)
    assert rec["weights"]["OFFICIAL"] == 50
    assert rec["weights"]["PARTY"] == 5
    assert rec["active"] is True


def test_create_policy_rejects_empty_name(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("invalid policy name"):
        contract.create_policy("", "description", 70, 20, 50, 45, 35, 25, 18, 10, 5)


def test_create_policy_rejects_invalid_threshold(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("invalid min score"):
        contract.create_policy("p", "description", 0, 20, 50, 45, 35, 25, 18, 10, 5)


def test_create_policy_rejects_weight_above_cap(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("invalid source weight"):
        contract.create_policy("p", "description", 70, 20, 101, 45, 35, 25, 18, 10, 5)


def test_policy_creator_can_deactivate(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    policy_id = create_policy(contract, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    contract.deactivate_policy(policy_id)
    assert policy(contract, policy_id)["active"] is False


def test_stranger_cannot_deactivate_policy(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm)
    policy_id = create_policy(contract, direct_vm, direct_alice)
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("only policy creator or owner"):
        contract.deactivate_policy(policy_id)


def test_open_dispute_records_deadlines(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    rec = dispute(contract, dispute_id)
    assert rec["status"] == "EVIDENCE_OPEN"
    assert rec["evidence_deadline"] == "2026-07-30T11:00:00Z"


def test_open_dispute_rejects_inactive_policy(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    policy_id = create_policy(contract, direct_vm, direct_alice)
    contract.deactivate_policy(policy_id)
    with direct_vm.expect_revert("inactive policy"):
        open_default(contract, direct_vm, direct_alice, policy_id)


def test_open_dispute_rejects_short_window(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("evidence window too short"):
        contract.open_dispute(1, "subject", "claimant", "respondent", 10, 7200, ZERO)


def test_submit_evidence_records_source_class(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_bob, dispute_id, "CLAIMANT", "OFFICIAL")
    ev = json.loads(contract.evidence_of(dispute_id, 0))
    assert ev["source_class"] == "OFFICIAL"


def test_submit_evidence_rejects_bad_side(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    with direct_vm.expect_revert("unsupported side"):
        submit(contract, direct_vm, direct_alice, dispute_id, "BOTH", "OFFICIAL")


def test_submit_evidence_rejects_bad_source(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    with direct_vm.expect_revert("unsupported source class"):
        submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "BLOG")


def test_submit_evidence_after_deadline_rejected(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    warp_to(direct_vm, "2026-07-30T11:00:01Z")
    with direct_vm.expect_revert("evidence window passed"):
        submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")


def test_submit_evidence_at_exact_deadline_allowed(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    warp_to(direct_vm, "2026-07-30T11:00:00Z")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    assert json.loads(contract.evidence_of(dispute_id, 0))["side"] == "CLAIMANT"


def test_submit_evidence_cap_enforced(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    for i in range(8):
        submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "PARTY", f"evidence {i}")
    with direct_vm.expect_revert("evidence cap reached"):
        submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "PARTY", "extra")


def test_lock_requires_evidence(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    with direct_vm.expect_revert("evidence required"):
        lock(contract, direct_vm, dispute_id, direct_alice)


def test_lock_sets_resolution_deadline(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    rec = dispute(contract, dispute_id)
    assert rec["status"] == "LOCKED"
    assert rec["resolution_deadline"] == "2026-07-30T12:00:00Z"


def test_resolve_claimant_wins_by_weighted_sources(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "AUDITED")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT", strength="HIGH"), item(1, "CLAIMANT", strength="MEDIUM")])
    contract.resolve_dispute(dispute_id)
    rec = dispute(contract, dispute_id)
    assert rec["verdict"] == "CLAIMANT"
    assert rec["claimant_score"] == 77


def test_resolve_respondent_wins_by_margin(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "RESPONDENT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "RESPONDENT", "PRIMARY")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "RESPONDENT", strength="HIGH"), item(1, "RESPONDENT", strength="HIGH")])
    contract.resolve_dispute(dispute_id)
    assert dispute(contract, dispute_id)["verdict"] == "RESPONDENT"


def test_party_claims_cannot_cross_threshold_alone(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "PARTY")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT", strength="HIGH")])
    contract.resolve_dispute(dispute_id)
    rec = dispute(contract, dispute_id)
    assert rec["verdict"] == "INCONCLUSIVE"
    assert rec["claimant_score"] == 5


def test_model_strength_is_clamped_to_safe_none(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT", strength="NUCLEAR")])
    contract.resolve_dispute(dispute_id)
    assert dispute(contract, dispute_id)["claimant_score"] == 0


def test_stale_evidence_cannot_score(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT", reliability="STALE", strength="HIGH")])
    contract.resolve_dispute(dispute_id)
    assert dispute(contract, dispute_id)["verdict"] == "EXTERNAL_FAILURE"


def test_unreadable_external_input_is_not_absence(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "NEITHER", reliability="UNREADABLE", strength="HIGH")])
    contract.resolve_dispute(dispute_id)
    rec = dispute(contract, dispute_id)
    assert rec["verdict"] == "EXTERNAL_FAILURE"
    assert rec["unusable_score"] == 50


def test_malformed_model_output_becomes_external_failure(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*GenLayer validator resolving source-weighted dispute evidence.*", "not json")
    contract.resolve_dispute(dispute_id)
    assert dispute(contract, dispute_id)["verdict"] == "EXTERNAL_FAILURE"


def test_fenced_json_model_output_is_recovered(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "AUDITED")
    lock(contract, direct_vm, dispute_id, direct_alice)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r".*GenLayer validator resolving source-weighted dispute evidence.*",
        "```json\n" + assessment([item(0, "CLAIMANT"), item(1, "CLAIMANT")]) + "\n```",
    )
    contract.resolve_dispute(dispute_id)
    assert dispute(contract, dispute_id)["verdict"] == "CLAIMANT"


def test_model_omitted_requested_item_does_not_shrink_set(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "AUDITED")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT")])
    contract.resolve_dispute(dispute_id)
    assessed = json.loads(contract.assessment_of(dispute_id))
    assert len(assessed["items"]) == 2
    assert assessed["items"][1]["reliability"] == "UNREADABLE"


def test_model_invented_item_is_discarded(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT"), item(9, "CLAIMANT")])
    contract.resolve_dispute(dispute_id)
    assessed = json.loads(contract.assessment_of(dispute_id))
    assert len(assessed["items"]) == 1


def test_keyed_model_items_are_accepted(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(
        r".*GenLayer validator resolving source-weighted dispute evidence.*",
        json.dumps(
            {
                "ok": True,
                "summary": "keyed item object",
                "items": {"0": item(0, "CLAIMANT")},
                "safe_error": "",
            }
        ),
    )
    contract.resolve_dispute(dispute_id)
    rec = dispute(contract, dispute_id)
    assert rec["verdict"] == "INCONCLUSIVE"
    assert rec["claimant_score"] == 50


def test_split_verdict_when_both_sides_cross_without_margin(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "PRIMARY")
    submit(contract, direct_vm, direct_alice, dispute_id, "RESPONDENT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "RESPONDENT", "PRIMARY")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT"), item(1, "CLAIMANT"), item(2, "RESPONDENT"), item(3, "RESPONDENT")])
    contract.resolve_dispute(dispute_id)
    assert dispute(contract, dispute_id)["verdict"] == "SPLIT"


def test_resolve_requires_locked_status(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    with direct_vm.expect_revert("locked dispute required"):
        contract.resolve_dispute(dispute_id)


def test_resolve_after_deadline_rejected(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    warp_to(direct_vm, "2026-07-30T12:00:01Z")
    with direct_vm.expect_revert("resolution deadline passed"):
        contract.resolve_dispute(dispute_id)


def test_resolve_at_exact_deadline_allowed(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "AUDITED")
    lock(contract, direct_vm, dispute_id, direct_alice)
    warp_to(direct_vm, "2026-07-30T12:00:00Z")
    mock_assessment(direct_vm, [item(0, "CLAIMANT"), item(1, "CLAIMANT")])
    contract.resolve_dispute(dispute_id)
    assert dispute(contract, dispute_id)["status"] == "RESOLVED"


def test_timeout_requires_deadline_passed(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    with direct_vm.expect_revert("resolution deadline active"):
        contract.timeout_dispute(dispute_id)


def test_timeout_at_exact_deadline_rejected(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    warp_to(direct_vm, "2026-07-30T12:00:00Z")
    with direct_vm.expect_revert("resolution deadline active"):
        contract.timeout_dispute(dispute_id)


def test_timeout_after_deadline_sets_inconclusive(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    warp_to(direct_vm, "2026-07-30T12:00:01Z")
    contract.timeout_dispute(dispute_id)
    assert dispute(contract, dispute_id)["status"] == "TIMED_OUT"


def test_callback_without_callback_fails(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "AUDITED")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT"), item(1, "CLAIMANT")])
    contract.resolve_dispute(dispute_id)
    with direct_vm.expect_revert("no callback"):
        contract.send_callback(dispute_id)


def test_archive_terminal_dispute(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "AUDITED")
    lock(contract, direct_vm, dispute_id, direct_alice)
    mock_assessment(direct_vm, [item(0, "CLAIMANT"), item(1, "CLAIMANT")])
    contract.resolve_dispute(dispute_id)
    contract.archive_dispute(dispute_id)
    assert dispute(contract, dispute_id)["status"] == "ARCHIVED"


def test_archive_nonterminal_rejected(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    with direct_vm.expect_revert("terminal dispute required"):
        contract.archive_dispute(dispute_id)


def test_double_archive_rejected(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    lock(contract, direct_vm, dispute_id, direct_alice)
    warp_to(direct_vm, "2026-07-30T12:00:01Z")
    contract.timeout_dispute(dispute_id)
    contract.archive_dispute(dispute_id)
    with direct_vm.expect_revert("already archived"):
        contract.archive_dispute(dispute_id)


def test_views_return_stats_status_verdict_and_assessment(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy, direct_vm)
    create_policy(contract, direct_vm, direct_alice)
    dispute_id = open_default(contract, direct_vm, direct_alice)
    submit(contract, direct_vm, direct_alice, dispute_id, "CLAIMANT", "OFFICIAL")
    assert contract.dispute_status(dispute_id) == "EVIDENCE_OPEN"
    assert contract.dispute_verdict(dispute_id) == "NONE"
    assert json.loads(contract.assessment_of(dispute_id))["ok"] is False
    stats = json.loads(contract.stats())
    assert stats["next_policy_id"] == "2"
    assert stats["total_evidence_items"] == "1"
