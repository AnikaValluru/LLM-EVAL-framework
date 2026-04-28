"""
Scorer module — evaluates LLM outputs against rubric criteria.

Supported check types:
  - contains_keywords   : output must include all listed keywords (case-insensitive)
  - excludes_keywords   : output must NOT include any listed keywords
  - max_length          : output must be <= N characters
  - min_length          : output must be >= N characters
  - starts_with         : output must begin with a given string
  - ends_with           : output must end with a given string
  - contains_all_of     : alias for contains_keywords
  - contains_any_of     : output must contain at least one of the listed strings
  - format_json         : output must be valid JSON
  - no_pii              : output must not contain common PII patterns
"""

import json
import re
from typing import Any


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def check_contains_keywords(output: str, keywords: list[str]) -> tuple[bool, str]:
    missing = [kw for kw in keywords if kw.lower() not in output.lower()]
    if missing:
        return False, f"missing keywords: {missing}"
    return True, "all keywords found"


def check_excludes_keywords(output: str, keywords: list[str]) -> tuple[bool, str]:
    found = [kw for kw in keywords if kw.lower() in output.lower()]
    if found:
        return False, f"forbidden keywords found: {found}"
    return True, "no forbidden keywords"


def check_max_length(output: str, max_len: int) -> tuple[bool, str]:
    length = len(output)
    if length > max_len:
        return False, f"output length {length} exceeds max {max_len}"
    return True, f"length {length} within max {max_len}"


def check_min_length(output: str, min_len: int) -> tuple[bool, str]:
    length = len(output)
    if length < min_len:
        return False, f"output length {length} below min {min_len}"
    return True, f"length {length} meets min {min_len}"


def check_starts_with(output: str, prefix: str) -> tuple[bool, str]:
    stripped = output.strip()
    if not stripped.startswith(prefix):
        return False, f"output does not start with '{prefix}'"
    return True, f"output starts with '{prefix}'"


def check_ends_with(output: str, suffix: str) -> tuple[bool, str]:
    stripped = output.strip()
    if not stripped.endswith(suffix):
        return False, f"output does not end with '{suffix}'"
    return True, f"output ends with '{suffix}'"


def check_contains_any_of(output: str, options: list[str]) -> tuple[bool, str]:
    found = [opt for opt in options if opt.lower() in output.lower()]
    if not found:
        return False, f"none of {options} found in output"
    return True, f"found: {found}"


def check_format_json(output: str, _: Any = None) -> tuple[bool, str]:
    # Try to extract JSON if surrounded by markdown fences
    cleaned = re.sub(r"```(?:json)?\n?(.*?)```", r"\1", output, flags=re.DOTALL).strip()
    try:
        json.loads(cleaned)
        return True, "valid JSON"
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e}"


def check_no_pii(output: str, _: Any = None) -> tuple[bool, str]:
    """Basic PII check: emails, phone numbers, SSN patterns."""
    patterns = {
        "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "phone": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    }
    found = {}
    for name, pattern in patterns.items():
        if re.search(pattern, output):
            found[name] = True
    if found:
        return False, f"PII detected: {list(found.keys())}"
    return True, "no PII detected"


# ---------------------------------------------------------------------------
# Check dispatcher
# ---------------------------------------------------------------------------

CHECK_REGISTRY = {
    "contains_keywords": check_contains_keywords,
    "contains_all_of": check_contains_keywords,
    "excludes_keywords": check_excludes_keywords,
    "max_length": check_max_length,
    "min_length": check_min_length,
    "starts_with": check_starts_with,
    "ends_with": check_ends_with,
    "contains_any_of": check_contains_any_of,
    "format_json": check_format_json,
    "no_pii": check_no_pii,
}


def score_output(output: str, rubric: dict) -> dict:
    """
    Score an LLM output against a rubric.

    Args:
        output: The raw text output from the LLM.
        rubric: Dict mapping check_type -> value (or True for no-arg checks).

    Returns:
        {
            "passed": bool,
            "score": float (0.0–1.0),
            "check_details": {check_name: {"passed": bool, "message": str}},
            "checks_passed": int,
            "checks_total": int,
        }
    """
    if not rubric:
        return {
            "passed": True,
            "score": 1.0,
            "check_details": {},
            "checks_passed": 0,
            "checks_total": 0,
        }

    check_details = {}
    checks_passed = 0

    for check_name, check_value in rubric.items():
        fn = CHECK_REGISTRY.get(check_name)
        if fn is None:
            check_details[check_name] = {"passed": False, "message": f"unknown check type: '{check_name}'"}
            continue

        try:
            if check_value is True or check_value is None:
                passed, message = fn(output)
            else:
                passed, message = fn(output, check_value)
        except Exception as e:
            passed, message = False, f"check error: {e}"

        check_details[check_name] = {"passed": passed, "message": message}
        if passed:
            checks_passed += 1

    checks_total = len(rubric)
    score = checks_passed / checks_total if checks_total > 0 else 1.0
    overall_passed = checks_passed == checks_total

    return {
        "passed": overall_passed,
        "score": score,
        "check_details": check_details,
        "checks_passed": checks_passed,
        "checks_total": checks_total,
    }
