"""
Data loader — reads docs/ JSON + contract text files into memory at startup.
Stored on app.state so services access data via FastAPI dependency injection,
not global variables or re-reading files per request. See Plan.md §4.

Fails loudly (raises on startup) if any expected file is missing.
"""

import json
import logging
import re
from pathlib import Path
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ContractData:
    """Raw contract data loaded from a .txt file."""
    id: str
    title: str
    raw_text: str


@dataclass
class StandardData:
    """A single company-approved standard from company_standards.json."""
    id: str
    category: str
    standard: str


@dataclass
class TestQuestion:
    """A public test question or missing-information case."""
    id: str
    contract_id: str
    question: str
    expected_behaviour: str | None = None  # only present in MI cases


@dataclass
class LoadedData:
    """All contest data loaded into memory."""
    contracts: dict[str, ContractData] = field(default_factory=dict)
    standards: dict[str, StandardData] = field(default_factory=dict)
    public_test_questions: list[TestQuestion] = field(default_factory=list)
    missing_info_cases: list[TestQuestion] = field(default_factory=list)


def _parse_contract_title(raw_text: str) -> str:
    """Extract the Title: line from a contract's raw text."""
    for line in raw_text.splitlines():
        if line.startswith("Title:"):
            return line[len("Title:"):].strip()
    return "Untitled"


def _parse_contract_id(raw_text: str) -> str:
    """Extract the Contract ID: line from a contract's raw text."""
    for line in raw_text.splitlines():
        if line.startswith("Contract ID:"):
            return line[len("Contract ID:"):].strip()
    return "UNKNOWN"


def load_all_data() -> LoadedData:
    """
    Load all contest data from the docs directory.
    Raises FileNotFoundError if any expected file is missing.
    """
    docs_dir: Path = settings.docs_dir
    data = LoadedData()

    # --- 1. Load company_standards.json ---
    standards_path = docs_dir / "company_standards.json"
    if not standards_path.exists():
        raise FileNotFoundError(f"Expected standards file not found: {standards_path}")

    with open(standards_path, "r", encoding="utf-8") as f:
        raw_standards = json.load(f)

    for item in raw_standards:
        std = StandardData(id=item["id"], category=item["category"], standard=item["standard"])
        data.standards[std.category] = std

    logger.info(f"Loaded {len(data.standards)} company standards")

    # --- 2. Load contract .txt files ---
    contracts_dir = docs_dir / "contracts"
    if not contracts_dir.exists():
        raise FileNotFoundError(f"Expected contracts directory not found: {contracts_dir}")

    contract_files = sorted(contracts_dir.glob("C-*.txt"))
    if not contract_files:
        raise FileNotFoundError(f"No contract files (C-*.txt) found in {contracts_dir}")

    for filepath in contract_files:
        raw_text = filepath.read_text(encoding="utf-8")
        contract_id = _parse_contract_id(raw_text)
        title = _parse_contract_title(raw_text)
        data.contracts[contract_id] = ContractData(
            id=contract_id,
            title=title,
            raw_text=raw_text,
        )

    logger.info(f"Loaded {len(data.contracts)} contracts")

    # --- 3. Load public_test_questions.json ---
    pq_path = docs_dir / "public_test_questions.json"
    if not pq_path.exists():
        raise FileNotFoundError(f"Expected public test questions file not found: {pq_path}")

    with open(pq_path, "r", encoding="utf-8") as f:
        raw_pq = json.load(f)

    for item in raw_pq:
        data.public_test_questions.append(
            TestQuestion(id=item["id"], contract_id=item["contract_id"], question=item["question"])
        )

    logger.info(f"Loaded {len(data.public_test_questions)} public test questions")

    # --- 4. Load missing_information_cases.json ---
    mi_path = docs_dir / "missing_information_cases.json"
    if not mi_path.exists():
        raise FileNotFoundError(f"Expected missing information cases file not found: {mi_path}")

    with open(mi_path, "r", encoding="utf-8") as f:
        raw_mi = json.load(f)

    for item in raw_mi:
        data.missing_info_cases.append(
            TestQuestion(
                id=item["id"],
                contract_id=item["contract_id"],
                question=item["question"],
                expected_behaviour=item.get("expected_behaviour"),
            )
        )

    logger.info(f"Loaded {len(data.missing_info_cases)} missing information cases")

    return data
