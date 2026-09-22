import pytest

from engine.deterministic import DerivedFeatureCandidate, ObservableRef, evaluate_derived_feature


def test_binary_operation_requires_right_operand() -> None:
    with pytest.raises(ValueError, match="requires a right observable"):
        DerivedFeatureCandidate("DF-1", "ADD", ObservableRef("a", "x"))


def test_unary_operation_rejects_right_operand() -> None:
    with pytest.raises(ValueError, match="unary and must not have"):
        DerivedFeatureCandidate("DF-1", "DELTA_FROM_PREVIOUS", ObservableRef("a", "x"), ObservableRef("b", "y"))


def test_rejects_unsupported_operation() -> None:
    with pytest.raises(ValueError, match="unsupported derived feature operation"):
        DerivedFeatureCandidate("DF-1", "MULTIPLY", ObservableRef("a", "x"), ObservableRef("b", "y"))


def test_evaluate_comparison_operations() -> None:
    assert evaluate_derived_feature("GREATER_OR_EQUAL", 2, 2) is True
    assert evaluate_derived_feature("GREATER_OR_EQUAL", 2, 4) is False
    assert evaluate_derived_feature("LESS_THAN", 1, 2) is True
    assert evaluate_derived_feature("EQUAL", 3, 3) is True


def test_evaluate_arithmetic_operations() -> None:
    assert evaluate_derived_feature("SUBTRACT", 5, 3) == 2
    assert evaluate_derived_feature("ABS_DIFFERENCE", 3, 5) == 2
    assert evaluate_derived_feature("ADD", 2, 3) == 5


def test_evaluate_divide_by_zero_raises() -> None:
    with pytest.raises(ValueError, match="divide by zero"):
        evaluate_derived_feature("DIVIDE", 5, 0)


def test_evaluate_delta_from_previous() -> None:
    assert evaluate_derived_feature("DELTA_FROM_PREVIOUS", 5, 3) == 2
    assert evaluate_derived_feature("DELTA_FROM_PREVIOUS", 5, None) is None
