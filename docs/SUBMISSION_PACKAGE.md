# Submission Package

## Title

Source-Weighted Dispute Resolver

## Notes

Source-Weighted Dispute Resolver is a reusable GenLayer primitive for contracts that must settle contested claims from weighted evidence. Importers create policies, open disputes, collect bounded text or URL evidence, then call one nondeterministic write. URL evidence is fetched contract-side with `gl.nondet.web.render`; validators classify the fetched excerpt/status into support, reliability, and strength buckets. Verdicts are deterministic code: weights, thresholds, and margins decide CLAIMANT, RESPONDENT, SPLIT, INCONCLUSIVE, or EXTERNAL_FAILURE.

Following reviewer feedback (Joaquin, Aug 4 2026), two security fixes were made and redeployed: (1) `lock_evidence` before the evidence deadline is now restricted to the dispute opener, policy creator, or contract owner — anyone can still lock once the deadline passes; (2) elevated source classes (`OFFICIAL`, `AUDITED`, `PRIMARY`, `EXPERT`, `NEWS`) now require explicit `authorize_source` grants from the policy creator/owner instead of being self-declared by the submitter. `COMMUNITY`/`PARTY` remain open.

StudioNet redeploy: `0x632ec86bD333bE77E4f0b46c7023Bf3A5d5786A9` (deploy tx `0x6f60209585f4c185d2f9404840211b82c2a8e303ccacb07709c3d81c8a0af96e`). Both fixes were exercised live against this deployment: an unauthorized account's `OFFICIAL` evidence submission reverted with no evidence recorded, and that account's early `lock_evidence` call reverted with the dispute staying `EVIDENCE_OPEN`. `resolve_dispute` on that dispute finalized (tx `0xb6f00a1fdc1f1093f924a03f02fb0545a5f53bbf3bfa071b8e5e856bd79808a9`) with verdict `INCONCLUSIVE` (weak, non-URL evidence scored below policy threshold — correct deterministic behavior). The fully deterministic `RESOLVED` → `send_callback` → `archive_dispute` path is covered with controlled mock assessments in the test suite. Lint passes for primitive and consumer; 52 direct tests pass.

## Evidence

- Contract (current, post-fix): `0x632ec86bD333bE77E4f0b46c7023Bf3A5d5786A9`
- Deploy tx: `0x6f60209585f4c185d2f9404840211b82c2a8e303ccacb07709c3d81c8a0af96e`
- Live resolve tx: `0xb6f00a1fdc1f1093f924a03f02fb0545a5f53bbf3bfa071b8e5e856bd79808a9`
- Prior deployment (pre-fix, superseded): `0xB1b739Ad0ed8db672BD1eA0F4341e84Ab7567bD8`
- Source path: `intelligent contract/source-weighted-dispute-resolver`

## Verification Commands

```powershell
genvm-lint check contracts\source_weighted_dispute_resolver.py --json
genvm-lint check examples\weighted_registry_consumer.py --json
pytest tests\direct\ -q
pytest tests\integration\ -q
```
