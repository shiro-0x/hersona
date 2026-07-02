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
from hersona.core.export import (
    EXPORT_FORMATS,
    export_blend,
    export_for_langchain_system_message,
    export_for_openai_assistants,
)
from hersona.core.intensity import (
    IntensityReport,
    expected_band,
    format_report,
    measure_intensity,
    pre_response_check_prompt,
)
from hersona.core.intensity import (
    verify as verify_intensity,
)
from hersona.core.persistent import (
    PersistentResult,
    run_persistent,
)
from hersona.core.presets import (
    Preset,
    PresetError,
    delete_preset,
    list_presets,
    load_preset,
    presets_root,
    save_preset,
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
from hersona.core.self_intro import (
    IntroLintResult,
    IntroViolation,
    lint_self_intro,
)
from hersona.core.soul import (
    SoulRenderResult,
    default_soul_path,
    render_soul,
    write_soul,
)
from hersona.core.use_cases import (
    available_use_cases,
    load_use_case,
    render_use_case_block,
    validate_use_case,
)
from hersona.core.weight import (
    WEIGHT_GUIDANCE,
    WeightLevel,
    catchphrase_subset,
    coerce_level,
    normalize_catchphrase,
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
    # use cases / Operating Modes
    "available_use_cases",
    "load_use_case",
    "render_use_case_block",
    "validate_use_case",
    # export
    "export_blend",
    "EXPORT_FORMATS",
    "export_for_openai_assistants",
    "export_for_langchain_system_message",
    # weight
    "WeightLevel",
    "WEIGHT_GUIDANCE",
    "catchphrase_subset",
    "coerce_level",
    "normalize_catchphrase",
    "suggest_weight",
    "weight_for_score",
    # intensity
    "IntensityReport",
    "expected_band",
    "pre_response_check_prompt",
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
    # presets
    "Preset",
    "PresetError",
    "save_preset",
    "load_preset",
    "list_presets",
    "delete_preset",
    "presets_root",
    # soul (SOUL.md persistence)
    "SoulRenderResult",
    "render_soul",
    "write_soul",
    "default_soul_path",
    # self-introduction lint
    "IntroLintResult",
    "IntroViolation",
    "lint_self_intro",
    # persistent (SOUL.md + config.yaml block coordination)
    "PersistentResult",
    "run_persistent",
]
