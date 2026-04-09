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
    apply_params_to_code,
    cleanup_strategy,
    extract_all_params,
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
            "gpt": (2.00, 8.00),  # gpt-5.4
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
    transfer_score: float = 0.0
    verdict: str = "unknown"
    scenario_gap: float = 0.0
    passive_fill_share: float = 0.0
    fragility_notes: list[str] = field(default_factory=list)
    by_symbol: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# JSON parsing helper
# ---------------------------------------------------------------------------


def _parse_json_response(text: str) -> dict[str, Any]:
    """Strip markdown fences and parse JSON from LLM response.

    Falls back to extracting code from ```python blocks if JSON parsing fails.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()

    try:
        result: dict[str, Any] = json.loads(text)
        return result
    except json.JSONDecodeError:
        pass

    # Fallback: extract code from ```python blocks
    import re

    code_match = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
        return {"code": code, "default_params": {}}

    # Second fallback: find "code" key with raw string
    code_match = re.search(r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
    if code_match:
        code = code_match.group(1).replace("\\n", "\n").replace('\\"', '"')
        return {"code": code, "default_params": {}}

    # Last resort: if it looks like Python code, use it directly
    if "def " in text and "class " in text:
        return {"code": text, "default_params": {}}

    result = json.loads(text)  # will raise — let it propagate
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
        worker_model: str = "claude-sonnet-4-20250514",
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

        # Memory health audit
        audit = self.memory.audit()
        _log.info("Memory audit: %s", audit)

        # Load second dataset for cross-day transfer evaluation
        self._eval_datasets: list[BacktestData] = [data]
        try:
            d2_prices = Path("data_raw/prices_round_0_day_-2.csv")
            d2_trades = Path("data_raw/trades_round_0_day_-2.csv")
            if d2_prices.exists() and d2_trades.exists():
                data_d2 = load_round_data(d2_prices, d2_trades)
                self._eval_datasets.append(data_d2)
                _log.info("Loaded day_-2 data for cross-day evaluation")
        except Exception:
            _log.warning("Could not load day_-2 data for cross-day evaluation")

        # Run full market onboarding (intel + profiles + opportunity allocation)
        self._onboarding = None
        self._asset_briefing = ""
        self._effort_allocation: dict[str, float] = {}
        try:
            from analytics.onboarding import onboard_new_round

            self._onboarding = onboard_new_round(self._eval_datasets)
            self._asset_briefing = self._onboarding.briefing
            self._effort_allocation = self._onboarding.effort_allocation
            for sym, profile in self._onboarding.profiles.items():
                _log.info(
                    "Asset %s: regime=%s, maker=%s, taker=%s, opportunity=%.2f, effort=%.0f%%",
                    sym,
                    profile.regime,
                    profile.maker_viability,
                    profile.taker_viability,
                    self._onboarding.opportunities[sym].score,
                    self._effort_allocation.get(sym, 0) * 100,
                )
        except Exception:
            self._asset_briefing = ""
            _log.warning("Could not run market onboarding")

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

        model = "gpt-5.4"
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
        models_to_try = ["gemini-3.1-pro-preview", "gemini-2.5-flash"]

        for attempt in range(5):
            # Fall back to 2.5-flash after 2 failed attempts with 3.1-pro
            model_name = models_to_try[0] if attempt < 2 else models_to_try[1]
            try:
                config = genai_types.GenerateContentConfig(
                    max_output_tokens=effective_max,
                    thinking_config=genai_types.ThinkingConfig(thinking_budget=16384),
                    http_options={"timeout": 120_000},  # 2 min timeout
                )
                response = self._gemini_client.models.generate_content(
                    model=model_name,
                    contents="\n\n".join(prompt_parts),
                    config=config,
                )
            except Exception as api_err:
                err_str = str(api_err)
                if any(k in err_str for k in ("503", "504", "UNAVAILABLE", "DEADLINE", "capacity")):
                    wait = 15 if attempt < 3 else 5  # longer wait for 3.1-pro, shorter for fallback
                    _log.warning(
                        "Gemini %s failed (attempt %d/5), retrying in %ds: %s",
                        model_name,
                        attempt + 1,
                        wait,
                        err_str[:100],
                    )
                    _time.sleep(wait)
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
        """Propose candidates: Gemini 3.1 Pro (1 idea) + GPT-5.4 (1 idea)."""
        candidates: list[dict[str, Any]] = []
        mechanics = self.memory.load_knowledge_file("mechanics.md")
        products = self._asset_briefing or self.memory.load_knowledge_file("product_briefs.md")
        evidence = self.memory.evidence_pack()
        family_dist = self.memory.family_distribution()
        platform_summary = self._load_platform_summary()

        # Build ideation prompt once (shared across models)
        system, messages = build_ideation_prompt(
            self.objective,
            self._strategy_examples,
            evidence,
            mechanics,
            products,
            1,
            round_num,
            family_dist,
            platform_summary,
            self._effort_allocation,
        )

        # Gemini ideation — 1 candidate
        if self._gemini_client is not None:
            try:
                result = self._call_gemini(messages, system=system)
                for c in result.get("candidates", [])[:1]:
                    c["source_model"] = "gemini"
                    candidates.append(c)
                    _log.info("Gemini proposed: %s", c["name"])
            except Exception as exc:
                _log.warning("Gemini ideation failed: %s", exc)

        # OpenAI GPT-5.4 ideation — 1 candidate
        if self._openai_client is not None:
            try:
                result = self._call_openai(messages, system=system)
                for c in result.get("candidates", [])[:1]:
                    c["source_model"] = "openai"
                    candidates.append(c)
                if candidates:
                    _log.info("OpenAI proposed: %s", candidates[-1]["name"])
            except Exception as exc:
                _log.warning("OpenAI ideation failed: %s", exc)

        _log.info("Ideation produced %d candidates total", len(candidates))
        return candidates

    # ---- Pipeline steps ---------------------------------------------------

    def _generate_code(self, candidate: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Generate strategy code (Opus call). Returns (code, default_params)."""
        import re as _re

        base = candidate.get("base_strategy", "market_maker")
        base_code = self._strategy_examples.get(base, "")
        system, messages = build_patching_prompt(candidate, base_code)

        # Call with higher token limit for code generation
        kwargs: dict[str, Any] = {
            "model": self.worker_model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        self.budget.record(
            self.worker_model, response.usage.input_tokens, response.usage.output_tokens
        )

        block = response.content[0]
        text: str = block.text if hasattr(block, "text") else str(block)

        # Extract code from ```python block
        code_match = _re.search(r"```python\s*\n(.*?)```", text, _re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
        else:
            # Fallback: try JSON parsing
            try:
                result = _parse_json_response(text)
                code = result.get("code", "")
            except (json.JSONDecodeError, ValueError):
                code = text.strip()

        # Fix escaped newlines if present
        if "\\n" in code and "\n" not in code:
            code = code.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')

        return code, {}

    @staticmethod
    def _classify_architecture(cr: CandidateResult) -> str:
        """Classify a candidate's architecture family."""
        from agents.taxonomy import classify_strategy

        return classify_strategy(cr.code or "", cr.description)

    def _refresh_opportunity(self) -> None:
        """Recompute opportunity allocation from latest per-asset evidence."""
        if not self._onboarding:
            return
        from analytics.onboarding import allocate_effort, compute_opportunity

        best_per_asset: dict[str, float] = {}
        for card in self.memory._cards:
            for sym, ae in card.get("by_symbol", {}).items():
                pnl = ae.get("raw_pnl", 0) if isinstance(ae, dict) else 0
                best_per_asset[sym] = max(best_per_asset.get(sym, 0), pnl)

        for sym in self._onboarding.profiles:
            self._onboarding.opportunities[sym] = compute_opportunity(
                self._onboarding.profiles[sym],
                self._onboarding.intel[sym],
                best_per_asset.get(sym, 0),
            )
        self._effort_allocation = allocate_effort(self._onboarding.opportunities)
        _log.info(
            "Opportunity refresh: %s",
            {sym: f"{w:.0%}" for sym, w in self._effort_allocation.items()},
        )

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

            # Validate before writing to disk
            from submission.checklist import validate_generated_code

            validation_errors = validate_generated_code(code)
            blockers = [e for e in validation_errors if not e.startswith("WARNING")]
            if blockers:
                cr.error = f"Validation failed: {'; '.join(blockers)}"
                _log.warning("Code validation failed for %s: %s", name, blockers)
                return cr

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

            # Deep evaluation with transfer scoring
            if cr.code:
                from experiments.evaluator import evaluate_candidate as deep_evaluate

                ev = deep_evaluate(
                    name=name,
                    strategy_source=cr.code,
                    params={},
                    datasets=self._eval_datasets,
                )
                cr.transfer_score = ev.transfer_score.score
                cr.verdict = ev.verdict
                cr.scenario_gap = ev.transfer_score.components.get("scenario_gap_penalty", 0.0)
                cr.passive_fill_share = ev.fill_diagnostics.passive_fill_share
                cr.fragility_notes = ev.fragility_notes
                cr.by_symbol = {
                    sym: {
                        "transfer_score": ae.transfer_score,
                        "raw_pnl": ae.raw_pnl,
                        "verdict": ae.verdict,
                        "passive_fill_share": ae.passive_fill_share,
                        "scenario_gap": ae.scenario_gap,
                        "fills": ae.fills,
                    }
                    for sym, ae in ev.by_symbol.items()
                }
                _log.info(
                    "Transfer score: %.4f, verdict=%s (%s)",
                    cr.transfer_score,
                    cr.verdict,
                    source,
                )

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
            "transfer_score": cr.transfer_score,
            "verdict": cr.verdict,
            "scenario_gap": cr.scenario_gap,
            "passive_fill_share": cr.passive_fill_share,
            "fragility_notes": cr.fragility_notes,
            "by_symbol": cr.by_symbol,
            "created_at": datetime.now(tz=UTC).isoformat(),
            "architecture_family": self._classify_architecture(cr),
            "platform_tested": False,
            "platform_pnl": None,
            "deprecated": False,
            "confidence": "low" if cr.transfer_score < 0.3 else "medium",
            "parent_strategy": None,
            "parent_round": None,
            "change_type": "new",
            "change_description": cr.description,
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

        # Evaluate random variants of the best candidate
        self._evaluate_variants(results, round_num)

        # Keep all cards with code — strategists need full history to avoid repeating
        self.memory._save_cards()

        best = max(
            results,
            key=lambda r: r.transfer_score,
            default=None,
        )

        # Update product knowledge with round results
        self._update_knowledge(results, round_num)

        # Refresh opportunity allocation based on latest evidence
        self._refresh_opportunity()

        # Diversity metrics
        families = [self._classify_architecture(r) for r in results if r.code and not r.error]
        unique_families = list(set(families))
        if len(unique_families) <= 1 and len(families) >= 2:
            _log.warning("LOW DIVERSITY: all %d candidates are %s", len(families), unique_families)
        _log.info(
            "Round %d diversity: %d families %s from %d candidates",
            round_num,
            len(unique_families),
            unique_families,
            len(results),
        )

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
            "diversity": {
                "families": unique_families,
                "n_families": len(unique_families),
                "all_same_family": len(unique_families) <= 1 and len(families) >= 2,
            },
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

        rounds_completed = 0

        # Preflight diversity check
        _log.info("Preflight family coverage: %s", self.memory.family_distribution())
        dead_ends = self.memory.detect_dead_ends()
        if dead_ends:
            _log.info("Preflight dead-end branches: %s", dead_ends[:5])

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

        # Save top 1 overall strategy (by transfer score)
        top_cards = sorted(
            [c for c in self.memory._cards if c.get("code") and c.get("pnl", 0) > 0],
            key=lambda c: c.get("transfer_score", 0),
            reverse=True,
        )[:1]

        for i, card in enumerate(top_cards, 1):
            name = card.get("name", f"best_{i}")
            code = card.get("code", "")
            if code:
                write_strategy_file(name, code, self.strategies_dir)
                register_strategy_import(name, self.init_path)
                _log.info("Saved #%d overall: %s (PnL=%.2f)", i, name, card.get("pnl", 0))

        # Assemble best per-asset strategy
        assembled_name = self._assemble_best_per_asset()

        best_name = top_cards[0]["name"] if top_cards else None
        best_pnl = top_cards[0].get("pnl", 0.0) if top_cards else 0.0

        # Recommend strategies for platform testing
        platform_recs: list[dict[str, Any]] = []
        try:
            from submission.policy import recommend_for_platform

            calibration_path = self.artifacts_dir / "calibration_data.json"
            recs = recommend_for_platform(self.memory, calibration_path, budget=3)
            for rec in recs:
                _log.info(
                    "Platform recommendation: %s (predicted=%d, reason=%s, family=%s)",
                    rec.strategy_name,
                    rec.local_prediction,
                    rec.submission_reason,
                    rec.architecture_family,
                )
                platform_recs.append(
                    {
                        "name": rec.strategy_name,
                        "prediction": rec.local_prediction,
                        "confidence": rec.confidence,
                        "reason": rec.submission_reason,
                        "family": rec.architecture_family,
                    }
                )
        except Exception:
            _log.exception("Platform recommendation failed — investigate")

        final: dict[str, Any] = {
            "rounds_completed": rounds_completed,
            "best_strategy": best_name,
            "best_pnl": best_pnl,
            "assembled_strategy": assembled_name,
            "platform_recommendations": platform_recs,
            "total_cost_usd": self.budget.estimated_cost(),
            "total_input_tokens": self.budget.total_input_tokens,
            "total_output_tokens": self.budget.total_output_tokens,
        }

        _console.print_json(data=final)
        return final

    def _assemble_best_per_asset(self) -> str | None:
        """Combine the best EMERALDS logic with best TOMATOES logic into one strategy."""
        cards_with_pp = [
            c
            for c in self.memory._cards
            if c.get("code") and c.get("per_product") and c.get("pnl", 0) > 0
        ]
        if not cards_with_pp:
            return None

        # Find best card per product by per-asset transfer score
        best_per_product: dict[str, dict[str, Any]] = {}
        for card in cards_with_pp:
            # Try by_symbol (new per-asset scores) first, fall back to per_product
            sym_data = card.get("by_symbol", {})
            for prod in card.get("per_product", {}):
                if prod in sym_data:
                    score = sym_data[prod].get("transfer_score", 0)
                else:
                    score = card.get("per_product", {}).get(prod, {}).get("fill_count", 0)
                if prod not in best_per_product or score > best_per_product[prod].get("_score", 0):
                    best_per_product[prod] = {**card, "_score": score}

        if len(best_per_product) < 2:
            return None

        # Check if both products use the same strategy — if so, no assembly needed
        names = [c.get("name") for c in best_per_product.values()]
        if len(set(names)) == 1:
            _log.info("Best per-asset is the same strategy for all products — no assembly needed")
            return None

        # Log what we're combining
        for prod, card in sorted(best_per_product.items()):
            _log.info(
                "Best for %s: %s (asset_score=%.4f, total_pnl=%.0f)",
                prod,
                card.get("name", "?"),
                card.get("_score", 0),
                card.get("pnl", 0),
            )

        # Generate combined code via Python combiner (LLM fallback)
        em_card = best_per_product.get("EMERALDS", {})
        tom_card = best_per_product.get("TOMATOES", {})
        em_code = em_card.get("code", "")
        tom_code = tom_card.get("code", "")

        assembled_name = "assembled_best_per_asset"
        combined_code = ""

        if em_code and tom_code:
            try:
                from submission.combine import combine_best_per_product

                output_path = self.artifacts_dir / "combined_strategy.py"
                combine_best_per_product(
                    emeralds_code=em_code,
                    emeralds_params=em_card.get("params", {}),
                    tomatoes_code=tom_code,
                    tomatoes_params=tom_card.get("params", {}),
                    output_path=output_path,
                )
                combined_code = output_path.read_text()
                _log.info("Combined strategy generated at %s", output_path)
            except Exception:
                _log.exception("Failed to generate combined strategy")

        # Validate assembled code
        assembled_score = 0.0
        assembled_verdict = "unknown"
        assembly_justified = False
        if combined_code:
            from submission.checklist import validate_generated_code

            errors = validate_generated_code(combined_code)
            if errors:
                _log.warning("Assembled strategy validation issues: %s", errors)

            # Evaluate assembled strategy through full pipeline
            try:
                from experiments.evaluator import evaluate_candidate as deep_evaluate

                ev = deep_evaluate(assembled_name, combined_code, {}, self._eval_datasets)
                assembled_score = ev.transfer_score.score
                assembled_verdict = ev.verdict
                _log.info(
                    "Assembled strategy: transfer=%.4f, verdict=%s",
                    assembled_score,
                    assembled_verdict,
                )

                # Only keep if >= 90% of best monolithic
                best_mono = max(
                    cards_with_pp,
                    key=lambda c: c.get("transfer_score", 0),
                )
                mono_score = best_mono.get("transfer_score", 0)
                assembly_justified = assembled_score >= mono_score * 0.9
                if not assembly_justified:
                    _log.info(
                        "Assembled (%.4f) < 90%% of monolithic (%.4f) — not justified",
                        assembled_score,
                        mono_score,
                    )
            except Exception:
                _log.exception("Failed to evaluate assembled strategy")

        self.memory.add_strategy_card(
            {
                "name": assembled_name,
                "source_model": "assembler",
                "description": "ASSEMBLED: Best per-asset combination. "
                + ", ".join(
                    f"{p}: {c.get('name', '?')}" for p, c in sorted(best_per_product.items())
                ),
                "pnl": 0,
                "transfer_score": assembled_score,
                "verdict": assembled_verdict,
                "round": 0,
                "params": {},
                "per_product": {},
                "strengths": "Per-asset cherry-pick. Test on platform to verify.",
                "status": "tested",
                "error": None,
                "products": sorted(best_per_product.keys()),
                "failure_reason": "" if assembly_justified else "worse than monolithic",
                "code": combined_code if combined_code else None,
                "assembly_diagnostics": {
                    "emeralds_source": em_card.get("name"),
                    "emeralds_score": em_card.get("_score", 0),
                    "tomatoes_source": tom_card.get("name"),
                    "tomatoes_score": tom_card.get("_score", 0),
                    "assembled_score": assembled_score,
                    "assembly_justified": assembly_justified,
                },
            }
        )

        _log.info(
            "Assembled strategy card created: %s (justified=%s)", assembled_name, assembly_justified
        )
        return assembled_name

    def _evaluate_variants(self, results: list[CandidateResult], round_num: int) -> None:
        """Generate and evaluate structured variants of the best candidate."""
        valid = [r for r in results if r.code and not r.error and r.transfer_score > 0]
        if not valid:
            return

        best = max(valid, key=lambda r: r.transfer_score)
        params = extract_all_params(best.code)
        if not params:
            _log.info("No extractable params for %s, skipping variants", best.name)
            return

        from experiments.evaluator import evaluate_candidate as deep_evaluate
        from experiments.evaluator import generate_structured_variants

        variants = generate_structured_variants(best.code, params, n_per_lane=2, seed=round_num)
        _log.info(
            "Evaluating %d structured variants of %s (exploit/orthogonal/mutation)",
            len(variants),
            best.name,
        )

        for vname, vparams, lane in variants:
            variant_name = f"{best.name}_{vname}"
            ev = deep_evaluate(
                name=variant_name,
                strategy_source=best.code,
                params=vparams,
                datasets=self._eval_datasets,
            )
            _log.info(
                "Variant %s [%s]: transfer=%.4f, verdict=%s (vs best %.4f)",
                variant_name,
                lane,
                ev.transfer_score.score,
                ev.verdict,
                best.transfer_score,
            )
            if ev.transfer_score.score > best.transfer_score:
                variant_code = apply_params_to_code(best.code, vparams)
                self.memory.add_strategy_card(
                    {
                        "name": variant_name,
                        "source_model": "variant",
                        "description": f"Variant of {best.name} (round {round_num})",
                        "pnl": ev.raw_pnl,
                        "round": round_num,
                        "params": vparams,
                        "per_product": {},
                        "strengths": f"Transfer score {ev.transfer_score.score:.4f}",
                        "status": "tested",
                        "code": variant_code,
                        "transfer_score": ev.transfer_score.score,
                        "verdict": ev.verdict,
                        "scenario_gap": ev.transfer_score.components.get(
                            "scenario_gap_penalty", 0.0
                        ),
                        "passive_fill_share": ev.fill_diagnostics.passive_fill_share,
                        "fragility_notes": ev.fragility_notes,
                        "parent_strategy": best.name,
                        "parent_round": round_num,
                        "change_type": lane,
                        "change_description": f"{lane} variant: {vparams}",
                    }
                )


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
    parser.add_argument("--worker-model", default="claude-sonnet-4-20250514")
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
