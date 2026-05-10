"""Tests for sanitizer v2 — reasoning block removal and CJK detection."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from translator.backends.sanitizer import (
    sanitize_subagent_output,
    strip_reasoning_blocks,
    collapse_blank_lines,
    detect_cjk_ratio,
    has_suspicious_cjk,
    THINK_PATTERNS,
)


# ── Reasoning block removal ──────────────────────────────────────────────

class TestStripReasoningBlocks:
    """Tests for strip_reasoning_blocks."""

    def test_simple_think(self):
        inp = "<think>english reasoning</think>Русский перевод"
        out = strip_reasoning_blocks(inp)
        assert out == "Русский перевод"

    def test_multiline_think(self):
        inp = "<think>\nstep1\nstep2\n</think>\nПеревод"
        out = strip_reasoning_blocks(inp)
        assert out == "\nПеревод"

    def test_thinking_tag(self):
        inp = "<thinking>analyzing context</thinking>Результат"
        out = strip_reasoning_blocks(inp)
        assert out == "Результат"

    def test_reasoning_tag(self):
        inp = "<reasoning>step by step</reasoning>Итог"
        out = strip_reasoning_blocks(inp)
        assert out == "Итог"

    def test_mixed_thinking_and_content(self):
        inp = "Вот перевод:\n<think>checking grammar</think>\nТекст"
        out = strip_reasoning_blocks(inp)
        assert out == "Вот перевод:\n\nТекст"

    def test_nested_like_blocks_do_not_break(self):
        """Non-matching tags like <thought> should not be touched."""
        inp = "<thought>keep this</thought>текст"
        out = strip_reasoning_blocks(inp)
        assert out == inp

    def test_case_insensitive(self):
        inp = "<THINK>uppercase</THINK>текст"
        out = strip_reasoning_blocks(inp)
        assert out == "текст"

    def test_no_reasoning_blocks(self):
        inp = "Чистый русский текст без блоков."
        out = strip_reasoning_blocks(inp)
        assert out == inp

    def test_multiple_think_blocks(self):
        inp = "<think>first</think>A<think>second</think>B"
        out = strip_reasoning_blocks(inp)
        assert out == "AB"

    def test_think_at_end(self):
        inp = "Normal text<think>trailing</think>"
        out = strip_reasoning_blocks(inp)
        assert out == "Normal text"


class TestCollapseBlankLines:
    """Tests for collapse_blank_lines."""

    def test_simple_collapse(self):
        inp = "A\n\n\n\nB"
        out = collapse_blank_lines(inp)
        assert out == "A\n\nB"

    def test_no_change(self):
        inp = "A\n\nB"
        out = collapse_blank_lines(inp)
        assert out == inp

    def test_many_blank_lines(self):
        inp = "A\n\n\n\n\n\n\nB"
        out = collapse_blank_lines(inp)
        assert out == "A\n\nB"

    def test_start_and_end(self):
        inp = "\n\n\nA\n\n\n\nB\n\n\n"
        out = collapse_blank_lines(inp)
        assert out == "\n\nA\n\nB\n\n"


# ── CJK detection ───────────────────────────────────────────────────────

class TestDetectCjkRatio:
    """Tests for detect_cjk_ratio."""

    def test_empty(self):
        assert detect_cjk_ratio("") == 0.0

    def test_pure_russian(self):
        assert detect_cjk_ratio("Привет, как дела?") == 0.0

    def test_one_chinese_char(self):
        # 好 is CJK Unified Ideograph
        r = detect_cjk_ratio("Привет好")
        assert 0.0 < r < 1.0

    def test_pure_chinese(self):
        assert detect_cjk_ratio("你好世界") == 1.0

    def test_mixed_text(self):
        # 最终 — 2 CJK chars out of 14 total nonspace chars
        r = detect_cjk_ratio("текст最终текст")
        assert 0.1 < r < 0.2  # 2/14 ≈ 0.143

    def test_hiragana_detected(self):
        r = detect_cjk_ratio("こんにちは")
        assert r > 0.5

    def test_katakana_detected(self):
        r = detect_cjk_ratio("テスト")
        assert r > 0.5

    def test_hangul_detected(self):
        r = detect_cjk_ratio("안녕하세요")
        assert r > 0.5


class TestHasSuspiciousCjk:
    """Tests for has_suspicious_cjk."""

    def test_low_ratio_no_suspicion(self):
        text = "Чистый русский текст."
        assert has_suspicious_cjk(text) is False

    def test_high_ratio_suspicion(self):
        text = "русский текст,最终классифицирующий"  # 2 CJK out of ~28
        assert has_suspicious_cjk(text) is True

    def test_threshold_respected(self):
        text = "A好"  # 1 out of 2 = 50% — exceeds default 2%
        assert has_suspicious_cjk(text, threshold=0.5) is False
        assert has_suspicious_cjk(text, threshold=0.01) is True


# ── Full sanitizer integration ──────────────────────────────────────────

class TestSanitizerIntegration:
    """Full pipeline tests for sanitize_subagent_output."""

    def test_think_removal(self):
        inp = "<think>english reasoning</think>Русский перевод"
        out, warnings = sanitize_subagent_output(inp, "test_001")
        assert "Русский перевод" in out
        assert any("reasoning" in w for w in warnings)

    def test_multiline_think_removal(self):
        inp = "<think>\nstep1\nstep2\n</think>\nПеревод текста после рассуждения"
        out, warnings = sanitize_subagent_output(inp, "test_002")
        assert "Перевод текста" in out

    def test_mixed_wrapper_and_think(self):
        inp = "Вот перевод:\n<think>reasoning</think>\nТекст"
        out, warnings = sanitize_subagent_output(inp, "test_003")
        assert "Текст" in out
        assert "Вот перевод" not in out

    def test_cjk_low_ratio_no_warning_comment(self):
        inp = "Чистый русский текст без китайских символов."
        out, warnings = sanitize_subagent_output(inp, "test_004")
        assert not out.startswith("<!-- WARNING:")

    def test_cjk_high_ratio_warning_comment(self):
        inp = "русский最终分类作品текст"
        out, warnings = sanitize_subagent_output(inp, "test_005")
        assert out.startswith("<!-- WARNING:")
        assert any("CJK" in w for w in warnings)

    def test_no_unicode_corruption(self):
        """Ensure legitimate characters are preserved."""
        inp = "Русский текст с Türkçe symbols, Eλληνικά, и emoji 🎉"
        out, warnings = sanitize_subagent_output(inp, "test_006")
        assert "Русский" in out
        assert "Türkçe" in out
        assert "Eλληνικά" in out
        assert "🎉" in out

    def test_short_output_flagged(self):
        out, warnings = sanitize_subagent_output("Hi", "test_007")
        assert "translation unavailable" in out

    def test_existing_wrappers_still_stripped(self):
        """Backward compatibility: old wrapper stripping still works."""
        inp = "Here is the translation:\nТекст перевода статьи об Эламе"
        out, warnings = sanitize_subagent_output(inp, "test_008")
        assert out == "Текст перевода статьи об Эламе"
        assert any("wrapper" in w.lower() for w in warnings)

    def test_non_translation_marker_detected(self):
        out, warnings = sanitize_subagent_output("I cannot translate this text", "test_009")
        assert any("non-translation" in w for w in warnings)

    def test_think_with_cjk_in_block(self):
        """CJK inside think block should not trigger CJK warning after removal."""
        inp = "<think>this 分类 is reasoning</think>Чистый русский перевод"
        out, warnings = sanitize_subagent_output(inp, "test_010")
        assert not out.startswith("<!-- WARNING:")
        assert "Чистый русский перевод" in out
