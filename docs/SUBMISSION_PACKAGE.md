# Submission Package

## Title

Source-Weighted Dispute Resolver

## Notes

Source-Weighted Dispute Resolver is a reusable GenLayer primitive for contracts that must settle contested claims from evidence with different trust levels. Importers create a policy with source-class weights, open a dispute, collect bounded evidence, then call consensus once to classify each item as supporting claimant/respondent/neither/conflicting with accepted/stale/unreadable/out-of-scope reliability and high/medium/low strength. The verdict is deterministic code, not model discretion: weights, thresholds, and margins decide CLAIMANT, RESPONDENT, SPLIT, INCONCLUSIVE, or EXTERNAL_FAILURE. StudioNet deploy: 0x897B810490a1e7E701D30D52067f21cccee5Db22. Live resolve tx 0x04d68bf3b617d318ed07cb445583942dd2f83d367ab335128c8990f519b2d033 produced CLAIMANT, score 50-0, after an OFFICIAL/HIGH/ACCEPTED evidence assessment. Lint passes for primitive and consumer; 40 direct tests pass.

## Evidence

- Contract: `0x897B810490a1e7E701D30D52067f21cccee5Db22`
- Deploy tx: `0xfe174c82ea0a75665b50371ebb00f3666d44ec1a485c3b0a67f871a3ed5042e6`
- Live resolve tx: `0x04d68bf3b617d318ed07cb445583942dd2f83d367ab335128c8990f519b2d033`
- Live archive tx: `0x55245a3c5376a47e5f5fc7213923577d5813de4e186575e18a78659eb7daaaf9`
- Source path: `intelligent contract/source-weighted-dispute-resolver`

## Verification Commands

```powershell
genvm-lint check contracts\source_weighted_dispute_resolver.py --json
genvm-lint check examples\weighted_registry_consumer.py --json
pytest tests\direct\ -q
pytest tests\integration\ -q
```

