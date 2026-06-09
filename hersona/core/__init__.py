"""hersona core — 属性ロジックの本体。"""

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

__all__ = [
    # compatibility
    "Attribute",
    "CompatibilityMatrix",
    "Relation",
    "load_matrix",
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
