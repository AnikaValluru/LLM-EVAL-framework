"""
LLM Evaluation Framework
Runs structured test cases against Claude API and scores outputs.
"""

import anthropic
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from scorer import score_output
from report import generate_report


def load_eval_suite(path: str) -> dict:
    """Load an evaluation suite from a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def run_eval(suite_path: str, output_dir: str = "results", model: str = "claude-haiku-4-5-20251001") -> dict:
    """
    Run all test cases in an eval suite against Claude.

    Args:
        suite_path: Path to the eval suite JSON file.
        output_dir: Directory to write result files.
        model: Claude model to use.

    Returns:
        Results dict with scores and metadata.
    """
    suite = load_eval_suite(suite_path)
    client = anthropic.Anthropic()

    suite_name = suite.get("name", "unnamed_suite")
    test_cases = suite.get("test_cases", [])
    system_prompt = suite.get("system_prompt", "")

    print(f"\n{'='*60}")
    print(f"Running eval suite: {suite_name}")
    print(f"Model: {model}")
    print(f"Test cases: {len(test_cases)}")
    print(f"{'='*60}\n")

    results = []

    for i, case in enumerate(test_cases):
        case_id = case.get("id", f"case_{i+1}")
        user_input = case.get("input", "")
        rubric = case.get("rubric", {})
        description = case.get("description", "")

        print(f"[{i+1}/{len(test_cases)}] Running: {case_id} — {description}")

        messages = [{"role": "user", "content": user_input}]

        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )
            output = response.content[0].text
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        except Exception as e:
            print(f"  ⚠️  API error: {e}")
            output = ""
            usage = {}

        score_result = score_output(output, rubric)
        passed = score_result["passed"]
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} — score: {score_result['score']:.2f} | checks: {score_result['check_details']}")

        results.append({
            "id": case_id,
            "description": description,
            "input": user_input,
            "output": output,
            "rubric": rubric,
            "score_result": score_result,
            "passed": passed,
            "usage": usage,
        })

        # Small delay to avoid rate limits
        time.sleep(0.3)

    # Summary stats
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    avg_score = sum(r["score_result"]["score"] for r in results) / total if total > 0 else 0

    summary = {
        "suite_name": suite_name,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": passed_count / total if total > 0 else 0,
        "avg_score": avg_score,
    }

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed_count}/{total} passed ({summary['pass_rate']*100:.1f}%)")
    print(f"Average score: {avg_score:.2f}")
    print(f"{'='*60}\n")

    full_results = {"summary": summary, "results": results}

    # Write results to file
    Path(output_dir).mkdir(exist_ok=True)
    safe_name = suite_name.lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"{output_dir}/{safe_name}_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(full_results, f, indent=2)
    print(f"Results saved to: {out_path}")

    # Generate markdown report
    report_path = generate_report(full_results, output_dir)
    print(f"Report saved to: {report_path}")

    return full_results


if __name__ == "__main__":
    import sys

    suite = sys.argv[1] if len(sys.argv) > 1 else "evals/customer_support.json"
    run_eval(suite)
