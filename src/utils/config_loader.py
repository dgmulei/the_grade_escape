from pathlib import Path
import json
from typing import Dict, Any
import logging

class ConfigLoader:
    def __init__(self, config_dir: str = "src/config"):
        self.config_dir = Path(config_dir)
        self.feedback_insights = self._load_json("josh_feedback_insights.json")
        self.preferences = self._load_json("josh_preferences.json")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        try:
            with open(self.config_dir / filename) as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load {filename}: {str(e)}")
            raise

    def get_feedback_criteria(self) -> Dict[str, Any]:
        return self.feedback_insights["validation_criteria"]

    def get_preferences(self) -> Dict[str, Any]:
        return self.preferences

    def get_rubric_rules(self) -> Dict[str, Any]:
        return self.feedback_insights["rubric_evaluation"]