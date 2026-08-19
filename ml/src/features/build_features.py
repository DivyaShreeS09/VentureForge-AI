"""Text feature construction for the industry classifier.

The model's only input feature is a single text string. This function is the single source of
truth for how (name, description) combine into that string — training and serving must both call
it so there is no train/serve skew. backend/app/ml/predictor.py mirrors this function exactly
(duplicated rather than cross-package-imported to keep the backend's runtime import graph
independent of ml/ — see docs/ARCHITECTURE.md); if you change the logic here, update it there too.
"""


def build_text_feature(name: str, description: str) -> str:
    name = (name or "").strip()
    description = (description or "").strip()
    if not name:
        return description
    if not description:
        return name
    return f"{name}. {description}"
