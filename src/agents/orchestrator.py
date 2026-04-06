"""Orchestrator — autonomous strategy development loop with multi-model ideation."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic
from rich.console import Console

from agents.memory import AgentMemory
from agents.prompts.ideation import build_ideation_prompt
from agents.prompts.patching import build_patching_prompt
from agents.tools.strategy_tools import (
    cleanup_strategy,
    extract_params,
    load_strategy_module,
    parse_platform_log,
    register_strategy_import,
    run_strategy_experiment,
    run_tests,
    write_strategy_file,
)
from data.parse_logs import BacktestData, load_round_data
from trader.logging_utils import get_logger

_log = get_logger("agents.orchestrator")
_console = Console()


# ---------------------------------------------------------------------------
# Budget tracking
# ---------------------------------------------------------------------------


@dataclass
class BudgetTracker:
    """Track token usage and estimated cost across multiple providers."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    budget_usd: float = 5.0
    _per_model: dict[str, tuple[int, int]] = field(default_factory=dict, repr=False)

    _PRICING: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "opus": (15.0, 75.0),
            "sonnet": (3.0, 15.0),
            "gpt": (0.55, 2.20),  # o4-mini (reasoning)
            "gemini": (2.00, 12.00),  # gemini-3.1-pro
        },
        repr=False,
    )

    def _tier(self, model: str) -> str:
        m = model.lower()
        if "opus" in m:
            return "opus"
        if "gpt" in m:
            return "gpt"
        if "gemini" in m:
            return "gemini"
        return "sonnet"

    def record(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Record token usage from one API call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        tier = self._tier(model)
        prev_in, prev_out = self._per_model.get(tier, (0, 0))
        self._per_model[tier] = (prev_in + input_tokens, prev_out + output_tokens)

    def estimated_cost(self) -> float:
        """Compute cost from per-model token counts."""
        total = 0.0
        for tier, (inp, out) in self._per_model.items():
            inp_rate, out_rate = self._PRICING.get(tier, (3.0, 15.0))
            total += inp / 1_000_000 * inp_rate + out / 1_000_000 * out_rate
        return total

    def over_budget(self) -> bool:
        """Check if estimated cost exceeds budget."""
        return self.estimated_cost() > self.budget_usd


# ---------------------------------------------------------------------------
# Candidate result
# ---------------------------------------------------------------------------


@dataclass
class CandidateResult:
    """Result of evaluating one candidate strategy."""

    name: str
    description: str
    source_model: str = ""
    code: str = ""
    faithful_metrics: dict[str, float] = field(default_factory=dict)
    test_passed: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# JSON parsing helper
# ---------------------------------------------------------------------------


def _parse_json_response(text: str) -> dict[str, Any]:
    """Strip markdown fences and parse JSON from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    result: dict[str, Any] = json.loads(text)
    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class Orchestrator:
    """Autonomous strategy development loop with multi-model ideation."""

    def __init__(
        self,
        objective: str,
        data: BacktestData,
        budget_usd: float = 5.0,
        max_rounds: int = 10,
        artifacts_dir: Path = Path("artifacts"),
        ideation_model: str = "claude-sonnet-4-20250514",
        worker_model: str = "claude-opus-4-20250514",
    ) -> None:
        from dotenv import load_dotenv

        load_dotenv(Path(".env"))

        self.objective = objective
        self.data = data
        self.budget = BudgetTracker(budget_usd=budget_usd)
        self.max_rounds = max_rounds
        self.artifacts_dir = artifacts_dir
        self.memory = AgentMemory(persist_path=artifacts_dir / "agent_memory.json")
        self.strategies_dir = Path("src/trader/strategies")
        self.init_path = self.strategies_dir / "__init__.py"
        self.ideation_model = ideation_model
        self.worker_model = worker_model
        self._strategy_examples = self._load_strategy_examples()

        # Anthropic client (always available)
        self.client = anthropic.Anthropic()

        # OpenAI client (optional)
        self._openai_client: Any = None
        try:
            import openai

            if os.environ.get("OPENAI_API_KEY"):
                self._openai_client = openai.OpenAI()
                _log.info("OpenAI client initialized")
        except ImportError:
            _log.info("openai not installed; skipping OpenAI ideation")

        # Gemini client (optional) — uses new google-genai SDK
        self._gemini_client: Any = None
        try:
            from google import genai as google_genai

            api_key = os.environ.get("GOOGLE_API_KEY")
            if api_key:
                self._gemini_client = google_genai.Client(api_key=api_key)
                _log.info("Gemini client initialized (gemini-3.1-pro with thinking)")
        except ImportError:
            _log.info("google-genai not installed; skipping Gemini ideation")

    def _load_strategy_examples(self) -> dict[str, str]:
        """Read existing strategy source code for prompt context."""
        examples: dict[str, str] = {}
        for name in ("market_maker", "fair_value", "inventory_mm"):
            path = self.strategies_dir / f"{name}.py"
            if path.exists():
                examples[name] = path.read_text()
        return examples

    # ---- LLM calls --------------------------------------------------------

    def _call_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Call Anthropic API, parse JSON response, track budget."""
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        self.budget.record(model, response.usage.input_tokens, response.usage.output_tokens)

        block = response.content[0]
        text: str = block.text if hasattr(block, "text") else str(block)

        try:
            return _parse_json_response(text)
        except json.JSONDecodeError:
            # Retry once
            retry_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    *messages,
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": "Output ONLY a valid JSON object."},
                ],
            }
            r2 = self.client.messages.create(**retry_kwargs)
            self.budget.record(model, r2.usage.input_tokens, r2.usage.output_tokens)
            block2 = r2.content[0]
            text2: str = block2.text if hasattr(block2, "text") else str(block2)
            return _parse_json_response(text2)

    def _call_openai(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Call OpenAI API, parse JSON response, track budget."""
        oai_messages: list[dict[str, str]] = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        oai_messages.extend(messages)

        model = "o4-mini"
        response = self._openai_client.chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=oai_messages,
            response_format={"type": "json_object"},
        )
        self.budget.record(model, response.usage.prompt_tokens, response.usage.completion_tokens)
        text: str = response.choices[0].message.content or ""
        return _parse_json_response(text)

    def _call_gemini(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Call Gemini API with thinking, parse JSON response, track budget."""
        from google.genai import types as genai_types

        prompt_parts: list[str] = []
        if system:
            prompt_parts.append(system)
        for msg in messages:
            prompt_parts.append(msg["content"])

        import time as _time

        effective_max = max(max_tokens, 16384)

        for attempt in range(3):
            try:
                response = self._gemini_client.models.generate_content(
                    model="gemini-3.1-pro-preview",
                    contents="\n\n".join(prompt_parts),
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=effective_max,
                        thinking_config=genai_types.ThinkingConfig(thinking_budget=16384),
                    ),
                )
            except Exception as api_err:
                err_str = str(api_err)
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    _log.warning("Gemini 503, retrying in 5s (attempt %d)", attempt + 1)
                    _time.sleep(5)
                    continue
                raise
            usage = response.usage_metadata
            self.budget.record(
                "gemini-2.5-flash",
                usage.prompt_token_count or 0,
                usage.candidates_token_count or 0,
            )
            text = response.text or ""
            try:
                return _parse_json_response(text)
            except json.JSONDecodeError:
                # Try regex extraction of JSON block
                import re

                match = re.search(r"\{[\s\S]*\"candidates\"[\s\S]*\}", text)
                if match:
                    try:
                        result: dict[str, Any] = json.loads(match.group())
                        return result
                    except json.JSONDecodeError:
                        pass
                if attempt == 0:
                    prompt_parts.append(
                        "Output ONLY a valid JSON object with a 'candidates' array."
                    )
                    continue
                _log.warning("Gemini JSON recovery failed, returning empty")
                return {"candidates": []}
        return {"candidates": []}  # all attempts exhausted

    def _load_platform_summary(self) -> str:
        """Load the latest platform log and return a summary string."""
        submissions_dir = Path("submissions")
        if not submissions_dir.exists():
            return ""
        # Find the most recent submission with logs
        latest_json: Path | None = None
        latest_mtime = 0.0
        for json_file in submissions_dir.rglob("*.json"):
            if json_file.stat().st_mtime > latest_mtime:
                latest_mtime = json_file.stat().st_mtime
                latest_json = json_file
        if latest_json is None:
            return ""
        try:
            result = parse_platform_log(latest_json)
            lines = [f"Platform PnL: {result['total_pnl']:.0f}"]
            for prod, pnl in result.get("per_product_pnl", {}).items():
                fills = result.get("per_product_fills", {}).get(prod, 0)
                lines.append(f"  {prod}: PnL={pnl:.0f}, fills={fills}")
            pos = result.get("final_positions", {})
            if pos:
                lines.append(f"  Final positions: {pos}")
            return "\n".join(lines)
        except Exception as exc:
            _log.warning("Could not parse platform log %s: %s", latest_json, exc)
            return ""

    # ---- Multi-model ideation ---------------------------------------------

    def _ideate(self, round_num: int) -> list[dict[str, Any]]:
        """Propose candidates: Gemini 3.1 Pro (1 idea) + o4-mini (1 idea)."""
        candidates: list[dict[str, Any]] = []
        top = self.memory.top_strategies(10)
        failed = self.memory.failed_strategies(5)
        mechanics = self.memory.load_knowledge_file("mechanics.md")
        products = self.memory.load_knowledge_file("product_briefs.md")

        best_card = self.memory.best_strategy_card()
        best_code = best_card.get("code", "") if best_card else ""

        # Load latest platform log summary if available
        platform_summary = self._load_platform_summary()

        # Gemini ideation — 1 candidate
        if self._gemini_client is not None:
            try:
                system, messages = build_ideation_prompt(
                    self.objective,
                    self._strategy_examples,
                    top,
                    failed,
                    mechanics,
                    products,
                    1,
                    round_num,
                    best_code,
                    best_card,
                    platform_summary,
                )
                result = self._call_gemini(messages, system=system)
                for c in result.get("candidates", [])[:1]:
                    c["source_model"] = "gemini"
                    candidates.append(c)
                    _log.info("Gemini proposed: %s", c["name"])
            except Exception as exc:
                _log.warning("Gemini ideation failed: %s", exc)

        # OpenAI o4-mini ideation — 1 candidate (reasoning model)
        if self._openai_client is not None:
            try:
                system, messages = build_ideation_prompt(
                    self.objective,
                    self._strategy_examples,
                    top,
                    failed,
                    mechanics,
                    products,
                    1,
                    round_num,
                    best_code,
                    best_card,
                    platform_summary,
                )
                result = self._call_openai(messages, system=system)
                for c in result.get("candidates", [])[:1]:
                    c["source_model"] = "openai"
                    candidates.append(c)
                _log.info("OpenAI proposed: %s", candidates[-1]["name"])
            except Exception as exc:
                _log.warning("OpenAI ideation failed: %s", exc)

        _log.info("Ideation produced %d candidates total", len(candidates))
        return candidates

    # ---- Pipeline steps ---------------------------------------------------

    def _generate_code(self, candidate: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Generate strategy code (Sonnet call). Returns (code, default_params)."""
        base = candidate.get("base_strategy", "market_maker")
        base_code = self._strategy_examples.get(base, "")
        system, messages = build_patching_prompt(candidate, base_code)
        result = self._call_anthropic(self.worker_model, messages, system=system)
        return result.get("code", ""), result.get("default_params", {})

    def _evaluate_candidate(
        self,
        candidate: dict[str, Any],
        round_num: int,
    ) -> CandidateResult:
        """Write, test, and run a candidate strategy."""
        raw_name = candidate.get("name", "unknown")
        name = f"agent_r{round_num}_{raw_name}"
        description = candidate.get("description", "")
        source = candidate.get("source_model", "unknown")
        cr = CandidateResult(name=name, description=description, source_model=source)

        try:
            code, params = self._generate_code(candidate)
            if not code:
                cr.error = "Empty code generated"
                return cr

            code = code.replace(f'@register("{raw_name}")', f'@register("{name}")')
            cr.code = code

            write_strategy_file(name, code, self.strategies_dir)
            register_strategy_import(name, self.init_path)
            load_strategy_module(name)

            project_root = Path(".")
            passed, test_output = run_tests(project_root)
            cr.test_passed = passed
            if not passed:
                cr.error = f"Tests failed:\n{test_output[:500]}"
                _log.warning("Tests failed for %s (%s)", name, source)
                return cr

            _log.info("Running sim for %s (%s)", name, source)
            cr.faithful_metrics = run_strategy_experiment(
                name, self.data, params=params, fast=False, artifacts_dir=self.artifacts_dir
            )
            _log.info("Sim PnL: %.2f (%s)", cr.faithful_metrics.get("total_pnl", 0.0), source)

        except Exception as exc:
            cr.error = str(exc)
            _log.warning("Error evaluating %s: %s", name, exc)
        finally:
            cleanup_strategy(name, self.strategies_dir, self.init_path)

        return cr

    def _build_strategy_card(self, cr: CandidateResult, round_num: int) -> dict[str, Any]:
        """Build a rich strategy card with per-product metrics, params, and analysis."""
        metrics = cr.faithful_metrics or {}
        pnl = metrics.get("total_pnl", 0.0)
        per_product: dict[str, Any] = metrics.get("per_product") or {}  # type: ignore[assignment]
        sharpe = metrics.get("sharpe", 0.0)
        max_dd = metrics.get("max_drawdown", 0.0)
        total_fills = metrics.get("total_fills", 0.0)
        max_pos = metrics.get("max_position", 0.0)

        # Extract actual params from code
        params: dict[str, Any] = {}
        if cr.code:
            params = extract_params(cr.code)

        # Auto-generate strengths
        strengths_list: list[str] = []
        if total_fills > 500:
            strengths_list.append("high fill rate")
        if max_pos < 40:
            strengths_list.append("good inventory control")
        if sharpe > 1.0:
            strengths_list.append("consistent returns")
        if per_product:
            fill_counts = [v.get("fill_count", 0) for v in per_product.values()]
            if fill_counts and min(fill_counts) > 0.3 * max(fill_counts):
                strengths_list.append("balanced across products")

        # Auto-generate failure reason with per-product detail
        failure_reason = ""
        if cr.error:
            failure_reason = f"code error: {cr.error[:100]}"
        elif pnl < -1000:
            details = []
            if max_pos > 70:
                details.append("hit position limits")
            for prod, pm in per_product.items():
                if pm.get("fill_count", 0) == 0:
                    details.append(f"no fills on {prod}")
            failure_reason = "catastrophic loss"
            if details:
                failure_reason += f" — {', '.join(details)}"
        elif pnl < 0:
            failure_reason = "negative PnL"
            if sharpe < -0.5:
                failure_reason += " — negative risk-adjusted returns"
        elif pnl == 0:
            failure_reason = "zero fills"

        card: dict[str, Any] = {
            "name": cr.name,
            "source_model": cr.source_model,
            "description": cr.description,
            "pnl": pnl,
            "round": round_num,
            "params": params,
            "per_product": per_product,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "total_fills": total_fills,
            "strengths": ", ".join(strengths_list) if strengths_list else "",
            "status": "",
            "error": cr.error,
            "products": sorted(self.data.products),
            "failure_reason": failure_reason,
        }

        if not cr.error and pnl >= 0 and cr.code:
            card["code"] = cr.code
        return card

    # ---- Main loop --------------------------------------------------------

    def _run_round(self, round_num: int) -> dict[str, Any]:
        """Execute one complete round."""
        _log.info("=== Round %d ===", round_num)

        candidates = self._ideate(round_num)
        if not candidates:
            return {"error": "No candidates proposed", "results": []}

        results: list[CandidateResult] = []
        for candidate in candidates:
            if self.budget.over_budget():
                _log.info("Budget reached during round")
                break
            cr = self._evaluate_candidate(candidate, round_num)
            results.append(cr)
            # Store strategy card immediately
            self.memory.add_strategy_card(self._build_strategy_card(cr, round_num))

        # Prune code from cards outside top 3 to limit memory size
        top3_names = {c["name"] for c in self.memory.top_strategies(3)}
        for card in self.memory._cards:
            if card.get("name") not in top3_names and "code" in card:
                del card["code"]
        self.memory._save_cards()

        best = max(
            results,
            key=lambda r: (r.faithful_metrics or {}).get("total_pnl", float("-inf")),
            default=None,
        )

        # Update product knowledge with round results
        self._update_knowledge(results, round_num)

        return {
            "results": [
                {
                    "name": r.name,
                    "description": r.description,
                    "source_model": r.source_model,
                    "faithful_metrics": r.faithful_metrics,
                    "error": r.error,
                    "code": r.code,
                }
                for r in results
            ],
            "best_name": best.name if best else None,
            "best_metrics": (best.faithful_metrics or {}) if best else {},
        }

    def _update_knowledge(self, results: list[CandidateResult], round_num: int) -> None:
        """Append round results to product_briefs.md so knowledge accumulates."""
        briefs_path = self.memory._knowledge_dir / "product_briefs.md"
        if not briefs_path.exists():
            return

        lines: list[str] = [f"\n## Round {round_num} results\n"]
        for r in results:
            pnl = (r.faithful_metrics or {}).get("total_pnl", 0.0)
            if pnl > 1000:
                verdict = "GOOD"
            elif pnl > 500:
                verdict = "ok"
            elif pnl > 0:
                verdict = "weak"
            else:
                verdict = "BAD"
            lines.append(
                f"- {r.name} ({r.source_model}): PnL={pnl:.0f} [{verdict}] — {r.description[:80]}\n"
            )

        with open(briefs_path, "a") as f:
            f.writelines(lines)

    def run(self) -> dict[str, Any]:
        """Main orchestrator loop."""
        _log.info(
            "Starting orchestrator: objective=%r, budget=$%.2f, max_rounds=%d",
            self.objective,
            self.budget.budget_usd,
            self.max_rounds,
        )

        best_overall_code: str = ""
        best_overall_name: str = ""
        best_overall_pnl: float = float("-inf")

        rounds_completed = 0

        for round_num in range(1, self.max_rounds + 1):
            if self.budget.over_budget():
                _log.info(
                    "Budget exhausted ($%.4f / $%.2f)",
                    self.budget.estimated_cost(),
                    self.budget.budget_usd,
                )
                break

            summary = self._run_round(round_num)
            rounds_completed = round_num

            # Store ALL candidates' results so every model sees what everyone tried
            all_results_summary = [
                {
                    "name": r.get("name", ""),
                    "source_model": r.get("source_model", ""),
                    "description": r.get("description", ""),
                    "pnl": (r.get("faithful_metrics") or {}).get("total_pnl"),
                    "error": r.get("error"),
                }
                for r in summary.get("results", [])
            ]
            self.memory.add(
                {
                    "round": round_num,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                    "metrics": summary.get("best_metrics", {}),
                    "all_candidates": all_results_summary,
                    "best_name": summary.get("best_name"),
                }
            )

            for r in summary.get("results", []):
                pnl = (r.get("faithful_metrics") or {}).get("total_pnl", float("-inf"))
                if pnl > best_overall_pnl and r.get("code"):
                    best_overall_pnl = pnl
                    best_overall_code = r["code"]
                    best_overall_name = r["name"]

        # Parameter sweep on best strategy (no LLM needed, pure grid search)
        if best_overall_code and best_overall_name:
            _log.info("Running parameter sweep on best strategy: %s", best_overall_name)
            sweep_pnl, sweep_code = self._parameter_sweep(best_overall_code, best_overall_name)
            if sweep_pnl > best_overall_pnl:
                _log.info("Sweep improved PnL: %.2f -> %.2f", best_overall_pnl, sweep_pnl)
                best_overall_pnl = sweep_pnl
                best_overall_code = sweep_code

        if best_overall_code and best_overall_name:
            _log.info("Writing best strategy: %s (PnL=%.2f)", best_overall_name, best_overall_pnl)
            write_strategy_file(best_overall_name, best_overall_code, self.strategies_dir)
            register_strategy_import(best_overall_name, self.init_path)

        final: dict[str, Any] = {
            "rounds_completed": rounds_completed,
            "best_strategy": best_overall_name or None,
            "best_pnl": best_overall_pnl if best_overall_pnl > float("-inf") else 0.0,
            "total_cost_usd": self.budget.estimated_cost(),
            "total_input_tokens": self.budget.total_input_tokens,
            "total_output_tokens": self.budget.total_output_tokens,
        }

        _console.print_json(data=final)
        return final

    def _parameter_sweep(self, code: str, name: str) -> tuple[float, str]:
        """Try parameter variations on the best strategy. Returns (best_pnl, best_code)."""
        import re

        best_pnl = float("-inf")
        best_code = code

        sweep_values: dict[str, list[float]] = {
            "order_size": [8, 10, 12, 15, 18, 20],
            "unwind_threshold": [40, 50, 60, 70],
            "ema_alpha": [0.10, 0.15, 0.20, 0.25, 0.30],
        }

        # Try each parameter independently (not full grid — too many combos)
        for param, values in sweep_values.items():
            for val in values:
                # Replace the default value in p.get("param", DEFAULT)
                new_code = re.sub(
                    rf'(p\.get\("{param}",\s*)[^)]+(\))',
                    rf"\g<1>{val}\2",
                    code,
                )

                if new_code == code:
                    continue

                # Clean name for the sweep variant
                clean_val = str(val).replace(".", "p")
                sweep_name = f"psweep_{param}_{clean_val}"
                # Replace register decorator to match sweep name
                new_code = re.sub(
                    r'@register\("[^"]+"\)',
                    f'@register("{sweep_name}")',
                    new_code,
                )
                try:
                    write_strategy_file(sweep_name, new_code, self.strategies_dir)
                    register_strategy_import(sweep_name, self.init_path)
                    load_strategy_module(sweep_name)
                    metrics = run_strategy_experiment(
                        sweep_name, self.data, fast=False, artifacts_dir=self.artifacts_dir
                    )
                    pnl = metrics.get("total_pnl", 0.0)
                    _log.info("Sweep %s=%s: PnL=%.2f", param, val, pnl)
                    if pnl > best_pnl:
                        best_pnl = pnl
                        best_code = new_code
                except Exception as exc:
                    _log.warning("Sweep %s=%s failed: %s", param, val, exc)
                finally:
                    cleanup_strategy(sweep_name, self.strategies_dir, self.init_path)

        return best_pnl, best_code


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the orchestrator."""
    parser = argparse.ArgumentParser(description="Autonomous strategy development loop")
    parser.add_argument("--objective", required=True, help="Optimization objective")
    parser.add_argument("--data-prices", required=True, type=Path, help="Prices CSV path")
    parser.add_argument("--data-trades", required=True, type=Path, help="Trades CSV path")
    parser.add_argument("--budget", type=float, default=5.0, help="Max spend in USD")
    parser.add_argument("--max-rounds", type=int, default=10, help="Max optimization rounds")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--ideation-model", default="claude-sonnet-4-20250514")
    parser.add_argument("--worker-model", default="claude-opus-4-20250514")
    args = parser.parse_args()

    data = load_round_data(args.data_prices, args.data_trades)

    orch = Orchestrator(
        objective=args.objective,
        data=data,
        budget_usd=args.budget,
        max_rounds=args.max_rounds,
        artifacts_dir=args.artifacts_dir,
        ideation_model=args.ideation_model,
        worker_model=args.worker_model,
    )

    orch.run()


if __name__ == "__main__":
    main()
