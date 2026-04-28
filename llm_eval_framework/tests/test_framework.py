"""
Tests for the LLM Evaluation Framework.

Covers:
  - scorer.py: all check types, edge cases, scoring math
  - report.py: report generation
  - eval_runner.py: suite loading, result structure
"""

import json
import os
import sys
import pytest
from pathlib import Path

# Add parent dir to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from scorer import (
    score_output,
    check_contains_keywords,
    check_excludes_keywords,
    check_max_length,
    check_min_length,
    check_starts_with,
    check_ends_with,
    check_contains_any_of,
    check_format_json,
    check_no_pii,
)
from report import generate_report
from eval_runner import load_eval_suite


# ===========================================================================
# scorer.py — individual check functions
# ===========================================================================

class TestContainsKeywords:
    def test_all_present(self):
        passed, msg = check_contains_keywords("Hello, this is a refund request.", ["refund", "hello"])
        assert passed is True

    def test_case_insensitive(self):
        passed, _ = check_contains_keywords("REFUND approved", ["refund"])
        assert passed is True

    def test_missing_keyword(self):
        passed, msg = check_contains_keywords("Hello there", ["refund"])
        assert passed is False
        assert "refund" in msg

    def test_partial_missing(self):
        passed, msg = check_contains_keywords("I want a refund please", ["refund", "apologize"])
        assert passed is False
        assert "apologize" in msg

    def test_empty_keywords(self):
        passed, _ = check_contains_keywords("anything", [])
        assert passed is True


class TestExcludesKeywords:
    def test_no_forbidden_words(self):
        passed, _ = check_excludes_keywords("I can help you with that.", ["kill", "harm"])
        assert passed is True

    def test_forbidden_word_present(self):
        passed, msg = check_excludes_keywords("Step 1: do this harmful thing", ["step 1"])
        assert passed is False

    def test_case_insensitive(self):
        passed, _ = check_excludes_keywords("CALM DOWN please", ["calm down"])
        assert passed is False

    def test_empty_forbidden_list(self):
        passed, _ = check_excludes_keywords("anything goes", [])
        assert passed is True


class TestMaxLength:
    def test_within_limit(self):
        passed, _ = check_max_length("Short response.", 100)
        assert passed is True

    def test_exactly_at_limit(self):
        text = "a" * 100
        passed, _ = check_max_length(text, 100)
        assert passed is True

    def test_exceeds_limit(self):
        text = "a" * 101
        passed, msg = check_max_length(text, 100)
        assert passed is False
        assert "101" in msg

    def test_empty_string(self):
        passed, _ = check_max_length("", 10)
        assert passed is True


class TestMinLength:
    def test_meets_minimum(self):
        passed, _ = check_min_length("Hello world, this is a decent response.", 20)
        assert passed is True

    def test_below_minimum(self):
        passed, msg = check_min_length("Hi", 10)
        assert passed is False
        assert "2" in msg

    def test_exactly_at_minimum(self):
        text = "a" * 10
        passed, _ = check_min_length(text, 10)
        assert passed is True


class TestStartsWith:
    def test_correct_prefix(self):
        passed, _ = check_starts_with("  Hello there!", "Hello")
        assert passed is True  # strips whitespace

    def test_wrong_prefix(self):
        passed, msg = check_starts_with("Goodbye world", "Hello")
        assert passed is False

    def test_empty_prefix(self):
        passed, _ = check_starts_with("anything", "")
        assert passed is True


class TestEndsWith:
    def test_correct_suffix(self):
        passed, _ = check_ends_with("Here is the answer.  ", "answer.")
        assert passed is True

    def test_wrong_suffix(self):
        passed, _ = check_ends_with("Here is the question?", "answer.")
        assert passed is False


class TestContainsAnyOf:
    def test_one_present(self):
        passed, _ = check_contains_any_of("I can look into that for you.", ["look into", "investigate"])
        assert passed is True

    def test_none_present(self):
        passed, msg = check_contains_any_of("I have no idea.", ["look into", "investigate", "resolve"])
        assert passed is False

    def test_case_insensitive(self):
        passed, _ = check_contains_any_of("LOOK INTO this", ["look into"])
        assert passed is True


class TestFormatJson:
    def test_valid_json_object(self):
        passed, _ = check_format_json('{"name": "Alice", "age": 30}')
        assert passed is True

    def test_valid_json_array(self):
        passed, _ = check_format_json('["apples", "bananas"]')
        assert passed is True

    def test_invalid_json(self):
        passed, msg = check_format_json("This is not JSON at all.")
        assert passed is False

    def test_json_in_markdown_fence(self):
        output = '```json\n{"key": "value"}\n```'
        passed, _ = check_format_json(output)
        assert passed is True

    def test_empty_string(self):
        passed, _ = check_format_json("")
        assert passed is False


class TestNoPii:
    def test_clean_output(self):
        passed, _ = check_no_pii("Thank you for contacting us. We will help you.")
        assert passed is True

    def test_email_detected(self):
        passed, msg = check_no_pii("Please contact john.doe@example.com for help.")
        assert passed is False
        assert "email" in msg

    def test_phone_detected(self):
        passed, msg = check_no_pii("Call us at 555-867-5309.")
        assert passed is False
        assert "phone" in msg

    def test_ssn_detected(self):
        passed, msg = check_no_pii("Your SSN is 123-45-6789.")
        assert passed is False
        assert "ssn" in msg


# ===========================================================================
# scorer.py — score_output integration
# ===========================================================================

class TestScoreOutput:
    def test_all_checks_pass(self):
        output = "I'm sorry to hear that. I will help you get a refund right away."
        rubric = {
            "contains_keywords": ["refund"],
            "max_length": 500,
        }
        result = score_output(output, rubric)
        assert result["passed"] is True
        assert result["score"] == 1.0
        assert result["checks_passed"] == 2
        assert result["checks_total"] == 2

    def test_one_check_fails(self):
        output = "Here are step-by-step instructions for hacking."
        rubric = {
            "excludes_keywords": ["step-by-step"],
            "min_length": 10,
        }
        result = score_output(output, rubric)
        assert result["passed"] is False
        assert result["score"] == 0.5
        assert result["checks_passed"] == 1
        assert result["checks_total"] == 2

    def test_all_checks_fail(self):
        output = "x"
        rubric = {
            "contains_keywords": ["refund"],
            "min_length": 100,
        }
        result = score_output(output, rubric)
        assert result["passed"] is False
        assert result["score"] == 0.0

    def test_empty_rubric(self):
        result = score_output("any output", {})
        assert result["passed"] is True
        assert result["score"] == 1.0

    def test_unknown_check_type(self):
        result = score_output("some output", {"nonexistent_check": "value"})
        assert result["passed"] is False
        assert "nonexistent_check" in result["check_details"]
        assert "unknown check type" in result["check_details"]["nonexistent_check"]["message"]

    def test_score_math_two_checks(self):
        output = "I can help with your refund request right away."
        rubric = {
            "contains_keywords": ["refund"],  # pass
            "min_length": 10,                 # pass
        }
        result = score_output(output, rubric)
        assert result["checks_total"] == 2
        assert result["checks_passed"] == 2
        assert result["score"] == 1.0

    def test_check_details_populated(self):
        result = score_output("hello world", {"contains_keywords": ["hello"]})
        assert "contains_keywords" in result["check_details"]
        assert result["check_details"]["contains_keywords"]["passed"] is True


# ===========================================================================
# eval_runner.py — suite loading
# ===========================================================================

class TestLoadEvalSuite:
    def test_loads_valid_suite(self, tmp_path):
        suite = {
            "name": "Test Suite",
            "system_prompt": "You are helpful.",
            "test_cases": [
                {"id": "t1", "input": "Hello", "rubric": {"min_length": 1}}
            ]
        }
        path = tmp_path / "suite.json"
        path.write_text(json.dumps(suite))
        loaded = load_eval_suite(str(path))
        assert loaded["name"] == "Test Suite"
        assert len(loaded["test_cases"]) == 1

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_eval_suite("/nonexistent/path/suite.json")

    def test_loads_customer_support_suite(self):
        """Ensure the bundled eval suite is valid."""
        suite_path = Path(__file__).parent.parent / "evals" / "customer_support.json"
        suite = load_eval_suite(str(suite_path))
        assert "name" in suite
        assert "test_cases" in suite
        assert len(suite["test_cases"]) > 0

    def test_loads_safety_suite(self):
        suite_path = Path(__file__).parent.parent / "evals" / "safety_guardrails.json"
        suite = load_eval_suite(str(suite_path))
        assert len(suite["test_cases"]) > 0

    def test_loads_json_output_suite(self):
        suite_path = Path(__file__).parent.parent / "evals" / "json_output.json"
        suite = load_eval_suite(str(suite_path))
        assert len(suite["test_cases"]) > 0


# ===========================================================================
# report.py — report generation
# ===========================================================================

class TestGenerateReport:
    def _make_results(self, passed=True):
        return {
            "summary": {
                "suite_name": "Test Suite",
                "model": "claude-haiku-4-5-20251001",
                "timestamp": "2026-04-28T12:00:00",
                "total": 1,
                "passed": 1 if passed else 0,
                "failed": 0 if passed else 1,
                "pass_rate": 1.0 if passed else 0.0,
                "avg_score": 1.0 if passed else 0.0,
            },
            "results": [
                {
                    "id": "t1",
                    "description": "Sample test",
                    "input": "Hello",
                    "output": "Hi there!",
                    "rubric": {"min_length": 1},
                    "passed": passed,
                    "score_result": {
                        "passed": passed,
                        "score": 1.0 if passed else 0.0,
                        "checks_passed": 1 if passed else 0,
                        "checks_total": 1,
                        "check_details": {
                            "min_length": {"passed": passed, "message": "length ok"}
                        },
                    },
                    "usage": {"input_tokens": 5, "output_tokens": 3},
                }
            ],
        }

    def test_report_file_created(self, tmp_path):
        results = self._make_results(passed=True)
        report_path = generate_report(results, str(tmp_path))
        assert Path(report_path).exists()

    def test_report_contains_suite_name(self, tmp_path):
        results = self._make_results()
        report_path = generate_report(results, str(tmp_path))
        content = Path(report_path).read_text()
        assert "Test Suite" in content

    def test_report_contains_pass_rate(self, tmp_path):
        results = self._make_results(passed=True)
        report_path = generate_report(results, str(tmp_path))
        content = Path(report_path).read_text()
        assert "100.0%" in content

    def test_report_shows_fail_status(self, tmp_path):
        results = self._make_results(passed=False)
        report_path = generate_report(results, str(tmp_path))
        content = Path(report_path).read_text()
        assert "FAIL" in content

    def test_report_shows_pass_status(self, tmp_path):
        results = self._make_results(passed=True)
        report_path = generate_report(results, str(tmp_path))
        content = Path(report_path).read_text()
        assert "PASS" in content

    def test_report_is_markdown(self, tmp_path):
        results = self._make_results()
        report_path = generate_report(results, str(tmp_path))
        assert report_path.endswith(".md")
        content = Path(report_path).read_text()
        assert content.startswith("# Eval Report:")
