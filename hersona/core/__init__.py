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
from hersona.core.recommend import (
    DEFAULT_QUIZ,
    QuizOption,
    QuizQuestion,
    Recommendation,
    recommend,
    score_answers,
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
    "score_answers",
    "recommend",
    # attach / blend
    "BlendResult",
    "available_attributes",
    "load_attribute",
    "render_blend",
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
