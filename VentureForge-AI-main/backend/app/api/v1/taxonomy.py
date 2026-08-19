from fastapi import APIRouter

from app.ml.positioning_taxonomy import TAXONOMY_VERSION, list_taxonomy_domains
from app.schemas.taxonomy import TaxonomyResponse

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


@router.get("", response_model=TaxonomyResponse)
def get_taxonomy() -> TaxonomyResponse:
    """Expose the active controlled venture-positioning taxonomy so the frontend positioning-
    correction control can populate its domain list from this live endpoint instead of a
    hand-duplicated TypeScript constant. Every domain is also a valid secondary-domain choice."""
    domains = list_taxonomy_domains()
    return TaxonomyResponse(
        taxonomy_version=TAXONOMY_VERSION,
        domains=domains,
        allowed_secondary_domains=[d["id"] for d in domains],
    )
