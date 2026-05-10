"""Orchestration layer — parallel translation coordination."""

from .parallel_translator import ParallelTranslator, ChunkResult

__all__ = ["ParallelTranslator", "ChunkResult"]