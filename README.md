# Source-Weighted Dispute Resolver

Standalone GenLayer Intelligent Contract primitive for evidence disputes. Importer contracts use it when they need a reusable way to settle contested claims from weighted source classes instead of trusting one reporter, one LLM call, or a backend.

## Why It Exists

A registry, escrow, insurer, or reputation system often needs one answer to a contested question: did the submitted evidence actually support the claimant, the respondent, neither, or both? A deterministic parser cannot read meaning. A price oracle cannot handle documents. A multisig or optimistic oracle moves judgement to humans. A single off-chain LLM gives one operator control. This contract keeps the semantic judgement inside validator consensus, then makes the actual verdict deterministic.

This is not an AI answer app. It does not sell summaries, advice, or recommendations. It does not merely validate JSON shape. The model output is only evidence classification; all scores, thresholds, status transitions, deadlines, callbacks, and archive rules are deterministic contract code.

## Mechanism

```mermaid
flowchart LR
    A["Importer creates policy"] --> B["Importer opens dispute"]
    B --> C["Parties submit capped evidence"]
    C --> D["Evidence is locked"]
    D --> E["Validators classify each item"]
    E --> F["Contract scores source weight x strength"]
    F --> G["Verdict stored for pull read or callback"]
```

Policy creators choose a minimum score, margin, and weights for `OFFICIAL`, `AUDITED`, `PRIMARY`, `EXPERT`, `NEWS`, `COMMUNITY`, and `PARTY` evidence. Evidence can be submitted as bounded text or as an HTTP(S) URL. URL evidence is fetched inside `resolve_dispute` with `gl.nondet.web.render`, capped into a compact excerpt, and passed to validators with an explicit `FETCHED` or `UNREADABLE` status. Validators classify each evidence item into enumerated buckets:

Source classes above `COMMUNITY`/`PARTY` (`OFFICIAL`, `AUDITED`, `PRIMARY`, `EXPERT`, `NEWS`) are not self-declared: the policy creator or contract owner must call `authorize_source(policy_id, account, source_class)` before that account may submit evidence tagged with that class. `submit_evidence` reverts with `EXPECTED: sender not authorized for source class ...` otherwise. `COMMUNITY` and `PARTY` stay open to any submitter since they already carry the lowest configurable weight. Authorization can be withdrawn with `revoke_source` and checked with the `is_source_authorized` view.

Closing the evidence window early is also gated: `lock_evidence` can only be called before the evidence deadline by the dispute opener, the policy creator, or the contract owner. Any account may call it once the evidence deadline has passed, so a dispute can never be stuck open forever, but no outside account can race to lock evidence shut the moment their own item lands.

- supports: `CLAIMANT`, `RESPONDENT`, `NEITHER`, `CONFLICTING`
- reliability: `ACCEPTED`, `STALE`, `UNREADABLE`, `OUT_OF_SCOPE`
- strength: `HIGH`, `MEDIUM`, `LOW`, `NONE`

The contract then applies deterministic scoring: high evidence gets 100 percent of source weight, medium gets 60 percent, low gets 30 percent, and unreliable/no-support evidence gets 0. Verdicts are `CLAIMANT`, `RESPONDENT`, `SPLIT`, `INCONCLUSIVE`, or `EXTERNAL_FAILURE`.

## Consensus Boundary

Nondeterminism is limited to one write method: `resolve_dispute`. It can perform up to one contract-side web render per URL evidence item, then asks validators to classify the locked evidence. It uses `gl.eq_principle.prompt_comparative` because the work is semantic judgement over external evidence.

Equivalence principle:

> Validator outputs are equivalent only when they make the same material classification for every requested evidence item: same support side, same reliability bucket, and same strength bucket. Wording, ordering, casing, and explanation phrasing may differ. A different verdict-relevant bucket, missing requested item, invented item, different party support, or different reliability/strength category is not equivalent.

Everything else is deterministic: access checks, length caps, source normalization, URL detection, fetch-status handling, time windows, counters, scoring, verdict thresholds, retries for inconclusive/external failure, callback rules, and archive rules.

Failure is explicit. Unparseable model output, omitted items, invented items, unreadable fetched sources, or unusable evidence cannot silently become proof. The contract records `EXTERNAL_FAILURE` or `INCONCLUSIVE` and leaves the dispute retryable until timeout.

## Reuse

Worked consumer: `examples/weighted_registry_consumer.py`. It does not duplicate resolver machinery; it stores a pending registry flag, points to the resolver, and accepts a callback or pull result.

| Importer | Policy difference | Consequence gated |
|---|---|---|
| registry | official/audited sources dominate | listing status |
| insurance pool | primary reports plus official data | payout eligibility |
| bounty vault | maintainer evidence vs claimant proof | release/refund path |
| reputation system | expert and official statements | score change |
| DAO permissions | governance record and audit trail | role grant/removal |

## API

Writes:

- `create_policy(name, description, min_score, margin, official_weight, audited_weight, primary_weight, expert_weight, news_weight, community_weight, party_weight) -> u256`
- `deactivate_policy(policy_id)`
- `authorize_source(policy_id, account, source_class)`
- `revoke_source(policy_id, account, source_class)`
- `open_dispute(policy_id, subject, claimant_position, respondent_position, evidence_window_seconds, resolution_window_seconds, callback) -> u256`
- `submit_evidence(dispute_id, side, source_class, uri_or_text, notes)`
- `lock_evidence(dispute_id)`
- `resolve_dispute(dispute_id)`
- `timeout_dispute(dispute_id)`
- `send_callback(dispute_id)`
- `archive_dispute(dispute_id)`

Views:

- `policy_of(policy_id)`
- `dispute_of(dispute_id)`
- `evidence_of(dispute_id, index)`
- `assessment_of(dispute_id)`
- `dispute_status(dispute_id)`
- `dispute_verdict(dispute_id)`
- `is_source_authorized(policy_id, account, source_class)`
- `stats()`

## Development

```powershell
genvm-lint check contracts\source_weighted_dispute_resolver.py --json
genvm-lint check examples\weighted_registry_consumer.py --json
pytest tests\direct\ -q
pytest tests\integration\ -q
```

StudioNet gltest nondeterministic tests are opt-in because the `gltest` path repeatedly canceled `resolve_dispute` before validator rounds with `NO_MAJORITY`, while the same deployed contract resolved successfully through `genlayer.cmd write`. Run the opt-in tests with:

```powershell
$env:RUN_STUDIONET_GLTEST_NONDET='1'
gltest tests\integration\ -v -s --network studionet
```

## Measured Status

Contract lines: 966. Consumer example lines: 80. Direct tests: 52 passing.

Lint:

- primitive: pass, 19 methods, 11 writes, 8 views
- consumer: pass, 4 methods, 2 writes, 2 views

StudioNet deployed contract:

`0xB1b739Ad0ed8db672BD1eA0F4341e84Ab7567bD8`

Deploy tx:

`0x173c0905e68b5c7c409041acbd49e0d909c865af4b60ae9c5ad06156c4d1c33e`

Live writes executed:

| Method | Tx | Result |
|---|---|---|
| `create_policy` | `0xffd140278c189df931ed5916bf778ffb3a1d5b322ee477934a8c7022460e6f1c` | policy `1`, accepted |
| `open_dispute` | `0x52326216cac834abbce25c426d6b60ab0bd96252e735af432d61380b7dda97aa` | dispute `1`, accepted |
| `submit_evidence` | `0x146d461ff35761cd58040934cbf5a1c397622ed97c442da4cf737b655ed17696` | URL evidence accepted |
| `lock_evidence` | `0x7f35469483bee8ef44ec6522e0ed78adc7727c2894727e18df92534fc7fa9108` | accepted |
| `resolve_dispute` | `0xf08a7487f91cf021743dd543ec64225237e88756b5c763c1b7d09a3ea88e8160` | accepted, contract-fetched URL evidence, verdict `CLAIMANT` |
| `send_callback` | `0x30c75fb0d5dedb53ddcbaeb87a366b1756f3c117b6385c3d9b5f44db665204de` | expected rollback: `EXPECTED: no callback` |
| `archive_dispute` | `0x9c7fb093165ed5c816f7d45d4351652c65cab31b2b4ec28147db47a7b4e3d617` | accepted |
| `create_policy` | `0x236ec05b80893708375af320ae2294d4ee9523cd75e7582e63347834175f1e95` | policy `2`, accepted |
| `deactivate_policy` | `0x987372fca9760e29a5aec7bdd0018971b84d539af563841233d4ac8bcd97c455` | accepted |

Live readback after resolution:

- `dispute_of(1)`: status `RESOLVED` before archive, verdict `CLAIMANT`, claimant score `50`, respondent score `0`
- `assessment_of(1)`: item `0` supports `CLAIMANT`, reliability `ACCEPTED`, strength `HIGH`, with reason based on the contract-fetched `https://example.com` excerpt
- final `dispute_status(1)`: `ARCHIVED`
- final `dispute_verdict(1)`: `CLAIMANT`
- final `stats()`: next policy `3`, next dispute `2`, active policies `1`, resolved `1`, archived `1`
- `policy_of(2)`: active `false`

`timeout_dispute` is covered in direct tests with controlled transaction time. It was not successfully executed against the live deployed address because the contract enforces a minimum 15-minute resolution window and the CLI path cannot time-warp StudioNet time.

## Honest Limits

This primitive is wrong for deterministic facts, numeric feeds, or cases where one authoritative API can be trusted directly. It also should not be used when evidence cannot be shared with validators.

URL fetching is intentionally conservative: it supports public HTTP(S) evidence available to GenLayer's renderer, caps fetched excerpts, and treats failed reads as `UNREADABLE` rather than proof. It does not authenticate private, paywalled, login-gated, or cryptographically signed documents by itself; importers should choose policy weights and accepted source classes accordingly.

StudioNet validator receipts can include `IDLE` after quorum. That occurred in accepted writes and did not affect final state. The live `resolve_dispute` tx reached `MAJORITY_AGREE` with 3 agree and 2 idle. The `gltest` StudioNet nondeterministic route canceled before validator rounds in earlier runs; the CLI deployment/write route is the measured on-chain proof for this submission.
