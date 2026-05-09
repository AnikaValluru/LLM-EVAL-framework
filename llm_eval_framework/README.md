# LLM Evaluation Framework

A lightweight, extensible framework for evaluating LLM outputs against structured rubrics — designed to demonstrate production-quality evaluation practices for AI systems.

Built as part of a portfolio project targeting AI Engineer and Applied AI roles that require hands-on experience designing evaluation frameworks (as specified in job descriptions at Anthropic, NBCUniversal, and similar companies).

---

## What It Does

This framework lets you define **eval suites** — structured sets of test cases with rubrics — and run them against the Claude API. For each test case it:

1. Sends the prompt to Claude
2. Scores the output against a rubric (keyword checks, format validation, length constraints, PII detection, etc.)
3. Produces a pass/fail result with a numeric score (0.0–1.0)
4. Generates a clean Markdown report summarizing results

---

## Why This Matters for AI Roles

Professional AI deployment isn't just about making something that *appears* to work — it's about making something that can be **validated and measured**. Every serious AI job description mentions evaluation:

> *"Implement evaluation frameworks to measure quality, reliability, and impact"* — NBCUniversal AI Engineer

> *"Skilled at creating and maintaining behavioral evaluations"* — Anthropic Prompt Engineer

> *"Evaluation frameworks and deployment at scale"* — Anthropic Forward Deployed Engineer

This project demonstrates exactly that skill.

---

## Project Structure

```
llm_eval_framework/
├── eval_runner.py          # Main runner — loads suites, calls Claude, scores results
├── scorer.py               # Scoring engine — 9 check types, extensible
├── report.py               # Markdown report generator
├── requirements.txt
│
├── evals/                  # Eval suites (JSON)
│   ├── customer_support.json
│   ├── safety_guardrails.json
│   └── json_output.json
│
├── results/                # Auto-generated results and reports (gitignored)
│
└── tests/
    ├── conftest.py
    └── test_framework.py   # 51 pytest tests — scorer, report, suite loading
```

---

## Setup

**Requirements:** Python 3.10+, an Anthropic API key

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/llm-eval-framework.git
cd llm-eval-framework

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY=your_key_here
```

---

## Running an Eval Suite

```bash
# Run the customer support eval suite (default)
python eval_runner.py

# Run a specific suite
python eval_runner.py evals/safety_guardrails.json
python eval_runner.py evals/json_output.json
```

**Example output:**
```
============================================================
Running eval suite: Customer Support Agent
Model: claude-haiku-4-5-20251001
Test cases: 5
============================================================

[1/5] Running: cs_001 — Refund request — must acknowledge and offer next step
  ✅ PASS — score: 1.00 | checks: {'contains_keywords': {'passed': True, ...}}
[2/5] Running: cs_002 — Password reset — must give actionable instructions
  ✅ PASS — score: 1.00 | ...
...

============================================================
RESULTS: 5/5 passed (100.0%)
Average score: 1.00
============================================================

Results saved to: results/customer_support_agent_20260428_120000.json
Report saved to:  results/customer_support_agent_20260428_120000_report.md
```

---

## Supported Check Types

| Check Type | Description | Example Value |
|---|---|---|
| `contains_keywords` | All keywords must be present (case-insensitive) | `["refund", "apologize"]` |
| `excludes_keywords` | None of these keywords may appear | `["step 1", "harm"]` |
| `contains_any_of` | At least one option must be present | `["resolve", "look into"]` |
| `min_length` | Output must be at least N characters | `50` |
| `max_length` | Output must be at most N characters | `600` |
| `starts_with` | Output must begin with this string | `"Dear"` |
| `ends_with` | Output must end with this string | `"."` |
| `format_json` | Output must be valid JSON | `true` |
| `no_pii` | Output must not contain emails, phones, or SSNs | `true` |

---

## Writing Your Own Eval Suite

Create a JSON file in `evals/`:

```json
{
  "name": "My Custom Suite",
  "system_prompt": "You are a helpful assistant.",
  "test_cases": [
    {
      "id": "my_001",
      "description": "Should give a short, friendly greeting",
      "input": "Say hello!",
      "rubric": {
        "contains_any_of": ["hello", "hi", "hey"],
        "max_length": 100
      }
    }
  ]
}
```

Then run:
```bash
python eval_runner.py evals/my_custom_suite.json
```

---

## Running Tests

```bash
pytest tests/ -v
```

The test suite covers:
- All 9 check types (unit tests for each)
- Edge cases: empty strings, boundary values, case sensitivity
- `score_output()` integration: scoring math, partial passes, empty rubrics, unknown checks
- Report generation: file creation, content validation, Markdown format
- Suite loading: valid suites, missing files, all 3 bundled suites

```
51 passed in 2.60s
```

---

## Sample Results

### Customer Support Agent
- 4/5 passed (80.0%)
- Average score: 0.95
- Notable: Claude correctly refused to share private customer data,
  stayed professional with an angry customer, and gave accurate 
  password reset instructions

### Key Insight
One test failed because Claude said "I understand your frustration" 
instead of "apologize" — demonstrating a real limitation of 
keyword-based evaluation and a natural next step: semantic similarity scoring

## Extending the Framework

To add a new check type:

1. Write a function `check_my_new_check(output: str, value) -> tuple[bool, str]` in `scorer.py`
2. Register it in `CHECK_REGISTRY`
3. Add tests in `tests/test_framework.py`
4. Use it in any eval suite JSON

---

## Bundled Eval Suites

| Suite | Description | # Cases |
|---|---|---|
| `customer_support.json` | Tests a support agent: refunds, PII safety, tone, instructions | 5 |
| `safety_guardrails.json` | Tests prompt injection resistance, harmful request refusal, jailbreaks | 5 |
| `json_output.json` | Tests structured output: valid JSON, correct field extraction | 5 |

---

## Tech Stack

- Python 3.10+
- [Anthropic Python SDK](https://github.com/anthropic-ai/anthropic-sdk-python)
- pytest

---

## Skills Demonstrated

- **Evaluation framework design** — defining rubrics, scoring pipelines, reporting
- **LLM API integration** — prompt construction, response handling, error recovery
- **Python software engineering** — modular design, type hints, extensible architecture
- **Automated testing** — 51 pytest tests covering unit, integration, and edge cases
- **Responsible AI** — safety evals, PII detection, guardrail testing

---

*Built by Anika Valluru — NJIT M.S. Artificial Intelligence*
