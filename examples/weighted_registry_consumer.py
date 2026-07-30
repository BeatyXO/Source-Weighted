# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json


@gl.contract_interface
class ISourceWeightedResolver:
    class View:
        def dispute_verdict(self, dispute_id: u256) -> str:
            pass

        def dispute_of(self, dispute_id: u256) -> str:
            pass

    class Write:
        pass


class WeightedRegistryConsumer(gl.Contract):
    resolver: Address
    accepted: TreeMap[str, str]
    last_callback: str

    def __init__(self, resolver: Address) -> None:
        self.resolver = self._coerce_address(resolver)
        self.accepted = TreeMap[str, str]()
        self.last_callback = ""

    @gl.public.write
    def import_resolved_dispute(self, dispute_id: u256, registry_key: str) -> None:
        if len(registry_key) == 0 or len(registry_key) > 120:
            raise gl.vm.UserError("EXPECTED: invalid registry key")
        resolver = ISourceWeightedResolver(self.resolver)
        verdict = resolver.view().dispute_verdict(dispute_id)
        if verdict != "CLAIMANT":
            raise gl.vm.UserError("EXPECTED: claimant verdict required")
        dispute = json.loads(resolver.view().dispute_of(dispute_id))
        self.accepted[registry_key] = json.dumps(
            {
                "dispute_id": str(dispute_id),
                "verdict": verdict,
                "claimant_score": str(dispute["claimant_score"]),
                "respondent_score": str(dispute["respondent_score"]),
            }
        )

    @gl.public.write
    def on_dispute_resolved(
        self,
        dispute_id: u256,
        policy_id: u256,
        verdict: str,
        claimant_score: u32,
        respondent_score: u32,
    ) -> None:
        self.last_callback = json.dumps(
            {
                "dispute_id": str(dispute_id),
                "policy_id": str(policy_id),
                "verdict": verdict,
                "claimant_score": str(claimant_score),
                "respondent_score": str(respondent_score),
            }
        )

    @gl.public.view
    def registry_entry(self, registry_key: str) -> str:
        if registry_key not in self.accepted:
            return "{}"
        return self.accepted[registry_key]

    @gl.public.view
    def callback_state(self) -> str:
        return self.last_callback

    def _coerce_address(self, value) -> Address:
        if isinstance(value, Address):
            return value
        return Address(value)
