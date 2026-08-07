# Handover: redeploy + flow test after security fix

## Context

Team review (Joaquin, Aug 4 2026) requested changes before acceptance:
1. Any account could submit one evidence item and immediately call `lock_evidence`,
   closing the evidence window before others could respond.
2. Source-weight classes (`OFFICIAL`, `AUDITED`, etc.) were self-declared by whoever
   submitted evidence — no trust check.

Both are **fixed and committed** on `main` at commit `d0f2034`
("Fix evidence-lock griefing and self-declared source classes"). Code, tests
(52 direct tests passing), and README/API docs are already updated and correct.

**What's left:** redeploy the fixed contract to StudioNet and re-run the live
write flow, then paste the new contract address / tx hashes into README.md and
docs/SUBMISSION_PACKAGE.md and docs/SUBMISSION_NOTES.txt (they still reference
the OLD pre-fix deployment `0xB1b739Ad0ed8db672BD1eA0F4341e84Ab7567bD8`).

## Why this is blocked

`https://studio.genlayer.com/api` (StudioNet) was returning:

```
GenLayer Studio is temporarily unavailable for maintenance.
```

as of 2026-08-07 ~11:24. Confirmed via both the `genlayer` CLI and a raw curl
POST to the RPC endpoint. This is an upstream outage, not a local config issue.
A wakeup was scheduled to retry ~10 min later but may not have completed —
check chat history / task notifications for a "redeploy" agent run after this
file was written before assuming nothing happened yet.

## What's already set up

A dedicated deployer account was created locally:

- Name: `source-weighted-dispute-resolver-deployer`
- Address: `0x21f9773ac4a6959c69233acae4d76a62c1f6bacf`
- Keystore: `C:\Users\DELL\.genlayer\keystores\source-weighted-dispute-resolver-deployer.json`
- Password used at creation: `sw-dispute-2026`
- It was set active at creation time. If it's no longer active, run:
  ```powershell
  genlayer.cmd account use source-weighted-dispute-resolver-deployer
  ```

It has **not been funded or used yet** — never got past the maintenance error
to check balance/deploy.

## Steps to resume

1. Check StudioNet is back:
   ```powershell
   curl -s https://studio.genlayer.com/api -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
   ```
   Should NOT return the maintenance error.

2. Confirm/select the deployer account and check it has a balance (StudioNet
   test accounts are normally auto-funded; if `account show` shows 0 balance,
   look for a faucet endpoint or ask the user):
   ```powershell
   genlayer.cmd account use source-weighted-dispute-resolver-deployer
   genlayer.cmd account show
   ```

3. Deploy the fixed contract:
   ```powershell
   genlayer.cmd deploy --contract contracts\source_weighted_dispute_resolver.py --rpc https://studio.genlayer.com/api
   ```
   Record the new contract address and deploy tx hash.

4. Run the live write flow against the new address, mirroring the sequence
   previously documented in README.md's "Live writes executed" table, but
   now including the new `authorize_source` step before submitting elevated
   evidence classes. Rough order:
   - `create_policy(...)` — same args pattern as `docs/SUBMISSION_PACKAGE.md`
     / README "Mechanism" section (see `tests/integration/test_full_surface_studionet.py`
     `policy_args()` for exact values).
   - `open_dispute(...)` (see `dispute_args()` in same test file).
   - `authorize_source(policy_id, <deployer address>, "OFFICIAL")` — **new
     required step**, must be called by policy creator/owner before
     submitting OFFICIAL-class evidence.
   - `submit_evidence(dispute_id, "CLAIMANT", "OFFICIAL", <uri or text>, notes)`.
   - `lock_evidence(dispute_id)` — now restricted; only works pre-deadline if
     called by the dispute opener, policy creator, or owner (the deployer
     account satisfies all three here, so this should just work).
   - `resolve_dispute(dispute_id)` — nondeterministic; may need
     `wait_interval`/`wait_retries` bumped, per README note about StudioNet
     sometimes cancelling with `NO_MAJORITY`.
   - `send_callback(dispute_id)` — expect a controlled revert
     (`EXPECTED: no callback`) since no callback contract was set, same as
     the original run.
   - `archive_dispute(dispute_id)`.
   - Also worth exercising once: `lock_evidence` called by a **third-party
     account** before the evidence deadline should now revert with
     `EXPECTED: only the dispute opener, policy creator, or contract owner...`,
     and `submit_evidence` with an unauthorized account claiming `OFFICIAL`
     should revert with `EXPECTED: sender not authorized for source class ...`.
     Capturing one of each as evidence directly demonstrates the fix to the
     reviewer.

   Alternatively, run the existing integration test suite against StudioNet
   instead of doing this by hand — it already encodes this exact flow
   (including the new `authorize_source` calls added for this fix):
   ```powershell
   $env:RUN_STUDIONET_GLTEST_NONDET='1'
   gltest tests\integration\ -v -s --network studionet
   ```
   `tests/integration/test_full_surface_studionet.py` and
   `test_convergence_studionet.py` both deploy fresh and run the full
   lifecycle; passing output is itself usable as evidence, but the reviewer's
   request was specifically for a **deployed address** on StudioNet plus live
   tx hashes, so still do a real `genlayer.cmd deploy` + `write` pass too, not
   just the test suite.

5. Update these files with the new address / tx hashes (replace the old
   `0xB1b739Ad0ed8db672BD1eA0F4341e84Ab7567bD8` references):
   - `README.md` — "StudioNet deployed contract", "Deploy tx", and the
     "Live writes executed" / "Live readback after resolution" sections.
   - `docs/SUBMISSION_PACKAGE.md`
   - `docs/SUBMISSION_NOTES.txt`

6. Commit with a message referencing the redeploy, e.g.:
   ```
   Redeploy fixed resolver to StudioNet and document live flow

   Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
   ```

7. Let the user know it's ready to resubmit to Joaquin, summarizing: what was
   fixed, new contract address, and that the lock/source-auth reverts were
   demonstrated live (or via the integration suite) on top of the deploy.

## Reminders / constraints from this session

- Don't fabricate tx hashes or addresses — if deploy/write fails, report the
  actual error, don't guess.
- This account was created fresh for this task; if funding fails, surface
  that to the user rather than trying unrelated accounts silently — several
  other unrelated deployer accounts exist in the local keystore
  (`amf-deployer`, `debatechain-deployer`, etc.) but they belong to other
  projects and shouldn't be reused here without asking.
- Deploying and sending transactions are regular dev/test actions on a
  public testnet (StudioNet), consistent with what the existing integration
  tests already do — no purchase, no mainnet funds, no credentials beyond
  the local testnet keystore created for this task.
