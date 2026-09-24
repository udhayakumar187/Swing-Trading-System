from typing import Dict, List, Optional, Type
from app.patterns.detectors.base import PatternDetector
from app.patterns.models import PatternDefinition, PatternCategory, OHLCVData, PatternDetection


class PatternRegistry:
    def __init__(self):
        self._detectors: Dict[str, PatternDetector] = {}
        self._by_category: Dict[PatternCategory, List[str]] = {}

    def register(self, detector: PatternDetector) -> None:
        name = detector.get_name()
        if name in self._detectors:
            raise ValueError(f"Detector with name '{name}' already registered")

        self._detectors[name] = detector
        category = detector.get_category()
        if category not in self._by_category:
            self._by_category[category] = []
        self._by_category[category].append(name)

    def unregister(self, name: str) -> bool:
        if name not in self._detectors:
            return False
        detector = self._detectors[name]
        category = detector.get_category()
        if category in self._by_category and name in self._by_category[category]:
            self._by_category[category].remove(name)
        del self._detectors[name]
        return True

    def get(self, name: str) -> Optional[PatternDetector]:
        return self._detectors.get(name)

    def get_by_category(self, category: PatternCategory) -> List[PatternDetector]:
        names = self._by_category.get(category, [])
        return [self._detectors[name] for name in names if name in self._detectors]

    def get_all(self) -> List[PatternDetector]:
        return list(self._detectors.values())

    def get_all_names(self) -> List[str]:
        return list(self._detectors.keys())

    def get_categories(self) -> List[PatternCategory]:
        return list(self._by_category.keys())

    def detect_all(
        self,
        data: OHLCVData,
        categories: Optional[List[PatternCategory]] = None,
        detector_names: Optional[List[str]] = None,
        context: Optional[Any] = None,
    ) -> List[PatternDetection]:
        all_detections = []

        detectors_to_run: List[PatternDetector] = []

        if detector_names:
            for name in detector_names:
                detector = self.get(name)
                if detector:
                    detectors_to_run.append(detector)
        elif categories:
            for cat in categories:
                detectors_to_run.extend(self.get_by_category(cat))
        else:
            detectors_to_run = self.get_all()

        for detector in detectors_to_run:
            if not detector.validate_data(data):
                continue
            try:
                detections = detector.detect(data, context)
                all_detections.extend(detections)
            except Exception as e:
                pass

        return all_detections

    def get_definition(self, name: str) -> Optional[PatternDefinition]:
        detector = self.get(name)
        return detector.definition if detector else None


_global_registry: Optional[PatternRegistry] = None


def get_registry() -> PatternRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = PatternRegistry()
    return _global_registry


def reset_registry() -> None:
    global _global_registry
    _global_registry = PatternRegistry()