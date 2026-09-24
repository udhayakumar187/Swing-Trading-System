from app.patterns.registry import get_registry, reset_registry
from app.patterns.detectors import (
    register_candlestick_patterns,
    register_chart_patterns,
    register_market_structure,
    register_indicator_patterns,
)
from app.patterns.divergence.detector import register_divergence_patterns
from app.patterns.harmonic.detector import register_harmonic_patterns
from app.patterns.wave.detector import register_wave_patterns
from app.patterns.volume.detector import register_volume_patterns


def initialize_pattern_engine(registry=None):
    if registry is None:
        registry = get_registry()

    register_candlestick_patterns(registry)
    register_chart_patterns(registry)
    register_market_structure(registry)
    register_indicator_patterns(registry)
    register_divergence_patterns(registry)
    register_harmonic_patterns(registry)
    register_wave_patterns(registry)
    register_volume_patterns(registry)

    return registry


def get_initialized_registry():
    registry = get_registry()
    if not registry.get_all():
        initialize_pattern_engine(registry)
    return registry