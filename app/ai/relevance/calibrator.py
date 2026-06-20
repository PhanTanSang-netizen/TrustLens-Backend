from dataclasses import dataclass


@dataclass(frozen=True)
class ThresholdProfile:
    name: str
    model_id: str
    dimension: int
    prompt_version: str
    calibrator_version: str = "provisional-1"


def build_threshold_profile(provider: str, model_id: str, dimension: int, prompt_version: str) -> ThresholdProfile:
    if provider == "gemini":
        name = f"{model_id}-{dimension}-c4-v2"
    else:
        normalized = model_id.replace("/", "-")
        name = f"{provider}-{normalized}-{dimension}-c4-v2"
    return ThresholdProfile(name=name, model_id=model_id, dimension=dimension, prompt_version=prompt_version)


def calibrate_probability(raw_relevance: float, profile: ThresholdProfile) -> float:
    del profile
    return round(max(0.0, min(1.0, raw_relevance)), 4)


def c4_score_from_probability(probability: float) -> int:
    if probability >= 0.85:
        return 20
    if probability >= 0.70:
        return 17
    if probability >= 0.55:
        return 14
    if probability >= 0.40:
        return 10
    if probability >= 0.25:
        return 7
    return 3
