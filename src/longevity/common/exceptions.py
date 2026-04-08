from __future__ import annotations


class LongevityBaseError(Exception):
    """Base error for all platform exceptions."""


class DataPipelineError(LongevityBaseError):
    """Error during data ingestion or processing."""


class ModelNotFoundError(LongevityBaseError):
    """Requested model artifact does not exist."""


class PredictionError(LongevityBaseError):
    """Model prediction failed."""


class InsufficientDataError(LongevityBaseError):
    """Not enough features provided to make a reliable prediction."""


class CausalInferenceError(LongevityBaseError):
    """Digital twin causal inference failed."""


class CoachError(LongevityBaseError):
    """AI coach interaction failed."""


class SafetyGuardrailError(LongevityBaseError):
    """Request blocked by safety guardrails."""


class FoodRecognitionError(LongevityBaseError):
    """Food image recognition failed."""
