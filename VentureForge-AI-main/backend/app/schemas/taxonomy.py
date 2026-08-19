"""Response contract for `GET /api/v1/taxonomy` (production-hardening phase).

Exposes the active controlled venture-positioning taxonomy (app.ml.positioning_taxonomy) over the
API so the frontend positioning-correction control can populate its domain list from the live
backend taxonomy instead of a hand-duplicated TypeScript constant — the previous approach silently
drifted whenever the backend taxonomy changed without a matching frontend edit.
"""

from __future__ import annotations

from pydantic import BaseModel


class TaxonomyDomain(BaseModel):
    """One controlled-taxonomy domain. `id` and `label` are currently identical (the taxonomy has
    no separate slug/display-name split) — both are exposed so a future taxonomy revision that adds
    a stable id distinct from a human-editable label doesn't require a frontend contract change.
    `description` is deterministically derived from the domain's own highest-weighted keywords/
    phrases — never hand-authored marketing copy, so it can never drift from what the matcher
    actually scores against.
    """

    id: str
    label: str
    description: str
    deployment_sectors: list[str]


class TaxonomyResponse(BaseModel):
    taxonomy_version: str
    domains: list[TaxonomyDomain]
    # Every domain is a valid secondary-domain choice too; exposed as its own field so a future
    # taxonomy revision could restrict secondary-eligible domains to a subset without breaking this
    # response shape.
    allowed_secondary_domains: list[str]
