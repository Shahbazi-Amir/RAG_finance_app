"""Provisional Product.v1 Claim↔Citation graph integrity, L1 only.

Checks the existing schema AND bidirectional referential integrity before
a fixture Answer is allowed to reach the product repository. This never
authenticates ENGINE/Producer, approves source locators, or makes an Answer
LIVE_VERIFIED; source strings and self-declared verification are untrusted.
No model provider, migration, Qdrant, network, or external resource is used.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

_SCHEMA_FILE = (Path(__file__).resolve().parents[3] /
                "packages/contracts/product.v1.schema.json")
_MAX_JSON_BYTES = 1_048_576


class CitationGraphDenied(Exception):
    """Public-safe, no source text/author/PII ever formatted in an error."""

    def __str__(self) -> str:
        return "CITATION_GRAPH_DENIED"


@dataclass(frozen=True)
class StructuralCitationReceipt:
    """Local graph check is not source authenticity, permission or approval."""

    claim_count: int
    citation_count: int
    reciprocal_links: int
    graph_consistent: bool = True
    source_verified: bool = False
    live_verified: bool = False
    authorizes_product_t3: bool = False


def _validator() -> Draft202012Validator:
    try:
        full = json.loads(_SCHEMA_FILE.read_text(encoding="utf-8"))
        if (not isinstance(full, dict)
                or full.get("$id") != "urn:ragfinance:product:v1"
                or full.get("$schema") != "https://json-schema.org/draft/2020-12/schema"):
            raise CitationGraphDenied()
        defs = full["$defs"]
        schema = {"$schema": full["$schema"],
                  "$defs": defs,
                  **defs["answer"]}
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema, format_checker=FormatChecker())
    except (OSError, ValueError, KeyError, TypeError, SchemaError):
        raise CitationGraphDenied() from None


def _validate_structural_https_url(url: str) -> None:
    """Syntax only: neither checks URL reachability nor authenticates a source.

    HTML clients must not be handed syntactically empty/misleading 'https://'
    links as verified citations. Owner-controlled allowlists and source authority
    remain separate, required release decisions.
    """
    if (not isinstance(url, str) or not url.startswith("https://")
            or any(ord(char) <= 32 for char in url)
            or "\\\\" in url):
        raise CitationGraphDenied()
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.netloc
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or (parsed.port is not None
                    and not 1 <= parsed.port <= 65535)):
            raise CitationGraphDenied()
    except (ValueError, UnicodeError):
        raise CitationGraphDenied() from None


def inspect_answer_citation_graph(answer: Mapping) -> StructuralCitationReceipt:
    """Validate only product.v1 shape and exact two-way ID graph.

    An Answer may be structurally valid and still be false, ungrounded,
    unauthorized or from a forged producer. Callers must independently
    authenticate and pin source/claims/locators before any live use.
    """
    if not isinstance(answer, Mapping):
        raise CitationGraphDenied()
    try:
        raw = json.dumps(answer, ensure_ascii=False, allow_nan=False)
        if len(raw.encode("utf-8")) > _MAX_JSON_BYTES:
            raise CitationGraphDenied()
        _validator().validate(answer)
        claims = answer["claims"]
        citations = answer["citations"]
        # format: uri without a configured FormatChecker is non-asserting in
        # JSON Schema. Check HTTPS authority syntax even when a synthetic
        # fixture self-declares resolution=verified; do not trust that claim.
        for citation in citations:
            locator = citation["source"]["locator"]
            if locator is not None and locator["kind"] == "url":
                _validate_structural_https_url(locator["url"])
        claim_ids = {claim["claim_id"] for claim in claims}
        citation_ids = {cite["citation_id"] for cite in citations}
        if len(claim_ids) != len(claims) or len(citation_ids) != len(citations):
            raise CitationGraphDenied()
        claim_links = {
            (claim["claim_id"], citation_id)
            for claim in claims for citation_id in claim["citation_ids"]
        }
        citation_links = {
            (claim_id, cite["citation_id"])
            for cite in citations for claim_id in cite["claim_ids"]
        }
        if (claim_links != citation_links
                or any(claim not in claim_ids or cite not in citation_ids
                       for claim, cite in claim_links | citation_links)):
            raise CitationGraphDenied()
        if citations and ({cite for _, cite in citation_links} != citation_ids):
            raise CitationGraphDenied()
        if claims and ({claim for claim, _ in claim_links} != claim_ids):
            raise CitationGraphDenied()

        # A structural LIVE_VERIFIED payload must not even self-declare an
        # unresolved source as a verified citation. External producer proof is
        # required separately; this test never promotes a declared locator.
        if answer["provenance"]["origin"] == "LIVE_VERIFIED":
            for cite in citations:
                source = cite["source"]
                if (source["resolution_status"] != "verified"
                        or source["attribution_status"] != "verified"
                        or source["locator"] is None):
                    raise CitationGraphDenied()
        return StructuralCitationReceipt(
            claim_count=len(claims), citation_count=len(citations),
            reciprocal_links=len(claim_links))
    except (OSError, TypeError, ValueError, KeyError, OverflowError,
            ValidationError, CitationGraphDenied):
        raise CitationGraphDenied() from None
