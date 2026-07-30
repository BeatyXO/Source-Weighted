# Decision Record

Chosen primitive: Source-Weighted Dispute Resolver.

It lets another contract define a source-weight policy, open a dispute, collect bounded evidence, then ask GenLayer validators to classify what each evidence item supports. The final verdict is deterministic code: source class weight, evidence strength, minimum score, and margin decide the result. Importers use it when a state transition depends on contested evidence rather than a simple price feed or one trusted reporter.

## Candidate Screen

| # | Candidate | Capability | Importers | Result |
|---|---|---|---|---|
| 1 | Evidence-Gated Intent Escrow | native value, consensus judgement | escrow, bounty, service protocols | built earlier |
| 2 | Bonded Claim Slashing Vault | native value, slashing | registries, insurance, reputation | built earlier |
| 3 | Source-Weighted Dispute Resolver | consensus judgement, contract callbacks | registries, courts, vaults | chosen |
| 4 | Visual Receipt Authenticity Gate | image evidence | reimbursements, attestations | strong, narrower reuse |
| 5 | Screenshot-State Change Guard | web render/image evidence | DAO ops, compliance monitors | collision risk with page-change primitives |
| 6 | Cross-Chain Proof Explanation Gate | EVM interop, judgement | bridges, rollup support | valuable but broad for this slot |
| 7 | Policy Snapshot Upgrade Guard | upgradeability, consensus | governed ICs | good primitive, less externally verifiable |
| 8 | Semantic KYC Claim Registry | embeddings, judgement | access registries | compliance-heavy, weaker public evidence |
| 9 | Contract-Deployed Arbitration Factory | factory/composition | dispute systems | mostly orchestration, less unique judgement |
| 10 | Reputation-Weighted Reporter Quorum | source reputation | oracle builders | too close to corroboration/reputation collision |
| 11 | Parametric Insurance Evidence Gate | native value, web evidence | insurance pools | closer to end-user product |
| 12 | Permissioned API Evidence Adapter | signed API/web get | private-data protocols | harder for reviewers to reproduce |

Distinct capabilities represented: native value, web/API evidence, image evidence, embeddings, EVM interop, factories, upgradeability, and contract-to-contract composition.

The two closest candidates are Source-Weighted Dispute Resolver and Reputation-Weighted Reporter Quorum. They are different: the chosen primitive weights evidence source classes per dispute policy; the discarded one maintains reporter reputation across submissions, which risks duplicating source-reputation oracle work.

If web access did not exist, the strongest pick would be Visual Receipt Authenticity Gate because visual evidence is still semantic, hard to fake with a parser, and clearly useful to other builders. I did not choose it because Source-Weighted Dispute Resolver is broader and can import text, URI excerpts, official statements, audits, news, and party evidence under one reusable scoring primitive.

Strongest discarded candidate: Cross-Chain Proof Explanation Gate. It has real trust value, but its scope is wider than a single weekly IC slot and depends more heavily on EVM-specific deployment context.

## Gate Check

Gate A, counterfactual: without GenLayer, a backend, multisig, or single LLM decides which evidence supports which party. The losing party must trust that operator.

Gate B, trust problem: claimant, respondent, registry owner, escrow vault, and downstream consumers may all depend on one answer. One party may supply evidence that benefits itself.

Gate C, judgement: the hard question is semantic: does this item support the claimant, respondent, neither, or both, and is it reliable enough to count?

Gate D, importability: a consumer only needs to open a dispute, wait for resolution, and read `dispute_verdict(dispute_id)` or receive `on_dispute_resolved(...)`.

Gate E, consequential state: verdicts can gate memberships, releases, slashing, listing status, permissions, or another contract's workflow.

Gate F, originality: it is not a source-reputation oracle, not a page watcher, and not a project-extracted contract. The reusable piece is policy-scored evidence classification with deterministic settlement.

