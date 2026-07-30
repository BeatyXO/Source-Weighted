# Submission Package

## Title

Source-Weighted Dispute Resolver

## Notes

Source-Weighted Dispute Resolver is a reusable GenLayer primitive for contracts that must settle contested claims from weighted evidence. Importers create policies, open disputes, collect bounded text or URL evidence, then call one nondeterministic write. URL evidence is fetched contract-side with `gl.nondet.web.render`; validators classify the fetched excerpt/status into support, reliability, and strength buckets. Verdicts are deterministic code: weights, thresholds, and margins decide CLAIMANT, RESPONDENT, SPLIT, INCONCLUSIVE, or EXTERNAL_FAILURE. StudioNet deploy: 0xB1b739Ad0ed8db672BD1eA0F4341e84Ab7567bD8. Live resolve tx 0xf08a7487f91cf021743dd543ec64225237e88756b5c763c1b7d09a3ea88e8160 produced CLAIMANT, score 50-0, after an OFFICIAL/HIGH/ACCEPTED contract-fetched URL assessment. Lint passes for primitive and consumer; 43 direct tests pass.

## Evidence

- Contract: `0xB1b739Ad0ed8db672BD1eA0F4341e84Ab7567bD8`
- Deploy tx: `0x173c0905e68b5c7c409041acbd49e0d909c865af4b60ae9c5ad06156c4d1c33e`
- Live resolve tx: `0xf08a7487f91cf021743dd543ec64225237e88756b5c763c1b7d09a3ea88e8160`
- Live archive tx: `0x9c7fb093165ed5c816f7d45d4351652c65cab31b2b4ec28147db47a7b4e3d617`
- Source path: `intelligent contract/source-weighted-dispute-resolver`

## Verification Commands

```powershell
genvm-lint check contracts\source_weighted_dispute_resolver.py --json
genvm-lint check examples\weighted_registry_consumer.py --json
pytest tests\direct\ -q
pytest tests\integration\ -q
```
