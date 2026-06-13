"""hersona core — 属性ロジックの本体。"""

from hersona.core.attach import (
    BlendResult,
    available_attributes,
    load_attribute,
    render_blend,
)
from hersona.core.authoring import (
    AuthoringError,
    ShareGuardError,
    ValidationGateError,
    assert_shareable,
    build_attribute,
    find_proper_noun_risks,
    list_user_attributes,
    override_attribute,
    save_attribute,
    user_attributes_root,
    validate_attribute,
)
from hersona.core.compatibility import (
    Attribute,
    CompatibilityMatrix,
    Relation,
    load_matrix,
)
from hersona.core.intensity import (
    IntensityReport,
    expected_band,
    format_report,
    measure_intensity,
)
from hersona.core.intensity import (
    verify as verify_intensity,
)
from hersona.core.recommend import (
    DEFAULT_QUIZ,
    DEFAULT_QUIZ_PATH,
    RECOMMEND_THRESHOLDS,
    QuizOption,
    QuizQuestion,
    Recommendation,
    WeightMagnitude,
    load_quiz,
    recommend,
    score_answers,
)
from hersona.core.weight import (
    WEIGHT_GUIDANCE,
    WeightLevel,
    catchphrase_subset,
    coerce_level,
    suggest_weight,
    weight_for_score,
)

__all__ = [
    # compatibility
    "Attribute",
    "CompatibilityMatrix",
    "Relation",
    "load_matrix",
    # recommend
    "QuizOption",
    "QuizQuestion",
    "Recommendation",
    "DEFAULT_QUIZ",
    "DEFAULT_QUIZ_PATH",
    "RECOMMEND_THRESHOLDS",
    "WeightMagnitude",
    "load_quiz",
    "score_answers",
    "recommend",
    # attach / blend
    "BlendResult",
    "available_attributes",
    "load_attribute",
    "render_blend",
    # weight
    "WeightLevel",
    "WEIGHT_GUIDANCE",
    "catchphrase_subset",
    "coerce_level",
    "suggest_weight",
    "weight_for_score",
    # intensity
    "IntensityReport",
    "expected_band",
    "format_report",
    "measure_intensity",
    "verify_intensity",
    # authoring
    "AuthoringError",
    "ValidationGateError",
    "ShareGuardError",
    "build_attribute",
    "override_attribute",
    "validate_attribute",
    "save_attribute",
    "list_user_attributes",
    "user_attributes_root",
    "find_proper_noun_risks",
    "assert_shareable",
]
