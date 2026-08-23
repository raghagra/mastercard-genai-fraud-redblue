from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Centralized project paths used by the backend pipeline."""

    root: Path
    schemas_dir: Path
    attack_cards_dir: Path
    generated_data_dir: Path
    processed_data_dir: Path
    outputs_dir: Path


def get_project_paths() -> ProjectPaths:
    root = Path(__file__).resolve().parents[2]
    return ProjectPaths(
        root=root,
        schemas_dir=root / "schemas",
        attack_cards_dir=root / "data" / "attack_cards",
        generated_data_dir=root / "data" / "generated",
        processed_data_dir=root / "data" / "processed",
        outputs_dir=root / "outputs",
    )

