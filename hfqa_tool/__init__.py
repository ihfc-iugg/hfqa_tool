# hfqa_tool/__init__.py

__all__ = ["main", "check_vocabulary", "quality_score"]
__version__ = "0.1.0"

from .Vocabulary_check import check_vocabulary
from .Combined_score import quality_score
from .main import main