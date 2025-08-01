from inspect import signature
from typing import Union

import numpy as np
import pandas as pd
import pytest
from sklearn.base import ClassifierMixin, RegressorMixin
from sklearn.calibration import _SigmoidCalibration
from sklearn.compose import ColumnTransformer
from sklearn.datasets import make_classification
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder

from mapie.calibration import TopLabelCalibrator
from mapie.metrics.calibration import top_label_ece
from mapie.metrics.calibration import expected_calibration_error

from mapie.calibration import VennABERSCalibrator

random_state = 20

CALIBRATORS = [
    "sigmoid", "isotonic", _SigmoidCalibration(), LinearRegression()
]

ESTIMATORS = [
    LogisticRegression(),
    RandomForestClassifier(random_state=random_state),
]

results = {
    "split": {
        "y_score": [
            [np.nan, 0.33333333, np.nan],
            [0.66666667, np.nan, np.nan],
            [np.nan, 0.33333333, np.nan],
            [np.nan, 0.33333333, np.nan],
            [np.nan, 0.33333333, np.nan],
            [np.nan, np.nan, 0.35635314],
            [np.nan, np.nan, 0.18501723],
        ],
        "top_label_ece": 0.3881,
    },
    "prefit": {
        "y_score": [
            [np.nan, np.nan, 0.85714286],
            [0.83333333, np.nan, np.nan],
            [np.nan, 0.83333333, np.nan],
            [np.nan, np.nan, 0.85714286],
            [np.nan, np.nan, 0.85714286],
            [np.nan, np.nan, 0.85714286],
            [0.83333333, np.nan, np.nan]
        ],
        "top_label_ece": 0.31349206349206343
    }
}

results_binary = {
    "split": {
        "y_score": [
            [0.74020596, np.nan],
            [0.4247601, np.nan],
            [np.nan, 0.66666667],
            [0.72980855, np.nan],
            [np.nan, 0.66666667],
            [0.81058943, np.nan],
            [0.7551083, np.nan],
            [0.59798388, np.nan],
            [np.nan, 0.66666667],
            [np.nan, 0.66666667],
        ],
        "top_label_ece": 0.315922,
        "ece": 0.554227,
    },
    "prefit": {
        "y_score": [
            [0.85714286, np.nan],
            [np.nan, 0.85714286],
            [np.nan, 0.85714286],
            [0.85714286, np.nan],
            [np.nan, 0.85714286],
            [0.85714286, np.nan],
            [0.85714286, np.nan],
            [0.85714286, np.nan],
            [np.nan, 0.85714286],
            [np.nan, 0.85714286]
        ],
        "top_label_ece": 0.1428571428571429,
        "ece": 0.3571428571428571
    },
}


X, y = make_classification(
    n_samples=20,
    n_classes=3,
    n_informative=4,
    random_state=random_state
)

X_, X_test, y_, y_test = train_test_split(
    X, y, test_size=0.33, random_state=random_state
)
X_train, X_calib, y_train, y_calib = train_test_split(
    X_, y_, test_size=0.33, random_state=random_state
)


def test_initialized() -> None:
    """Test that initialization does not crash."""
    TopLabelCalibrator()


def test_default_parameters() -> None:
    """Test default values of input parameters."""
    mapie_cal = TopLabelCalibrator()
    assert mapie_cal.calibrator is None
    assert mapie_cal.cv == "split"


def test_default_fit_params() -> None:
    """Test default sample weights and other parameters."""
    mapie_cal = TopLabelCalibrator()
    assert (
        signature(mapie_cal.fit).parameters["sample_weight"].default
        is None
    )
    assert (
        signature(mapie_cal.fit).parameters["calib_size"].default
        == 0.33
    )
    assert (
        signature(mapie_cal.fit).parameters["random_state"].default
        is None
    )
    assert (
        signature(mapie_cal.fit).parameters["shuffle"].default
        is True
    )
    assert (
        signature(mapie_cal.fit).parameters["stratify"].default
        is None
    )


def test_false_str_estimator() -> None:
    """Test invalid string input for calibrator."""
    with pytest.raises(
        ValueError,
        match=r".*Please provide a string in*",
    ):
        mapie_cal = TopLabelCalibrator(
            calibrator="not_estimator"
        )
        mapie_cal.fit(X, y)


def test_estimator_none() -> None:
    """Test that no input for calibrator will return a sigmoid"""
    mapie_cal = TopLabelCalibrator()
    mapie_cal.fit(X, y)
    assert isinstance(
        mapie_cal.calibrators[list(mapie_cal.calibrators.keys())[0]],
        _SigmoidCalibration
    )


def test_check_type_of_target() -> None:
    """Test the type of target."""
    X = [0.5, 0.2, 0.4, 0.8, 3.8]
    y = [0.4, 0.2, 3.6, 3, 0.2]
    mapie_cal = TopLabelCalibrator()
    with pytest.raises(
        ValueError,
        match=r".*Make sure to have one of the allowed targets:*"
    ):
        mapie_cal.fit(X, y)


def test_prefit_cv_argument() -> None:
    """Test that prefit method works"""
    est = RandomForestClassifier().fit(X, y)
    mapie_cal = TopLabelCalibrator(estimator=est, cv="prefit")
    mapie_cal.fit(X, y)


def test_split_cv_argument() -> None:
    """Test that split method works"""
    mapie_cal = TopLabelCalibrator(cv="split")
    mapie_cal.fit(X, y)


@pytest.mark.parametrize("cv", ["noprefit", "nosplit"])
def test_invalid_cv_argument(cv: str) -> None:
    """Test that other cv method does not work"""
    with pytest.raises(
        ValueError,
        match=r".*Invalid cv argument*",
    ):
        mapie_cal = TopLabelCalibrator(cv=cv)
        mapie_cal.fit(X, y)


def test_prefit_split_same_results() -> None:
    """Test that prefit and split method return the same result"""
    est = RandomForestClassifier(
        random_state=random_state
    ).fit(X_train, y_train)
    mapie_cal_prefit = TopLabelCalibrator(estimator=est, cv="prefit")
    mapie_cal_prefit.fit(X_calib, y_calib)

    mapie_cal_split = TopLabelCalibrator(
        estimator=RandomForestClassifier(random_state=random_state)
    )
    mapie_cal_split.fit(
        X_, y_, random_state=random_state
    )
    y_prefit = mapie_cal_prefit.predict_proba(X_test)
    y_split = mapie_cal_split.predict_proba(X_test)
    np.testing.assert_allclose(y_split, y_prefit)


def test_not_seen_calibrator() -> None:
    """
    Test that there is a warning if no calibration occurs
    due to no calibrator for this class.
    """
    with pytest.warns(
        UserWarning,
        match=r".*WARNING: This predicted label*"
    ):
        mapie_cal = TopLabelCalibrator()
        mapie_cal.fit(X, y)
        mapie_cal.calibrators.clear()
        mapie_cal.predict_proba(X)


@pytest.mark.parametrize("calibrator", CALIBRATORS)
@pytest.mark.parametrize("estimator", ESTIMATORS)
def test_shape_of_output(
    calibrator: Union[str, RegressorMixin],
    estimator: ClassifierMixin
) -> None:
    """Test that the size of the outputs are coherent."""
    mapie_cal = TopLabelCalibrator(
        estimator=estimator,
        calibrator=calibrator,
    )
    mapie_cal.fit(X, y)
    calib_ = mapie_cal.predict_proba(X)
    assert calib_.shape == (len(y), mapie_cal.n_classes_)


def test_number_of_classes_equal_calibrators() -> None:
    """
    Test that the number of calibrators is the same as the number
    of classes in the calibration step.
    """
    mapie_cal = TopLabelCalibrator()
    mapie_cal.fit(
        X=X_,
        y=y_,
        random_state=random_state
    )
    y_pred_calib_set = mapie_cal.single_estimator_.predict(X=X_calib)
    assert len(mapie_cal.calibrators) == len(np.unique(y_pred_calib_set))


def test_same_predict() -> None:
    """Test that the same prediction is made regardless of the calibration."""
    mapie_cal = TopLabelCalibrator()
    mapie_cal.fit(
        X=X_,
        y=y_,
        random_state=random_state
    )
    y_pred_calib_set = mapie_cal.single_estimator_.predict(X=X_test)
    y_pred_calib_set_through_predict = mapie_cal.predict(X=X_test)
    y_pred_calibrated_test_set = np.nanargmax(
        mapie_cal.predict_proba(X=X_test),
        axis=1
    )
    np.testing.assert_allclose(y_pred_calib_set, y_pred_calibrated_test_set)
    np.testing.assert_allclose(
        y_pred_calib_set,
        y_pred_calib_set_through_predict
    )


@pytest.mark.parametrize("cv", TopLabelCalibrator.valid_cv)
def test_correct_results(cv: str) -> None:
    """
    Test that the y_score and top label score from the test dataset result
    in the correct scores (in a multi-class setting).
    """
    mapie_cal = TopLabelCalibrator(cv=cv)
    mapie_cal.fit(
        X=X_,
        y=y_,
        random_state=random_state
    )
    pred_ = mapie_cal.predict_proba(X_test)
    top_label_ece_ = top_label_ece(y_test, pred_)
    np.testing.assert_array_almost_equal(
        np.array(results[cv]["y_score"]),
        np.array(pred_),
        decimal=2
    )
    np.testing.assert_allclose(  # type:ignore
        results[cv]["top_label_ece"],
        top_label_ece_,
        rtol=1e-2
    )


@pytest.mark.parametrize("cv", TopLabelCalibrator.valid_cv)
def test_correct_results_binary(cv: str) -> None:
    """
    Test that the y_score and top label score from the test dataset result
    in the correct scores (in a binary setting).
    """
    X_binary, y_binary = make_classification(
        n_samples=10,
        n_classes=2,
        n_informative=4,
        random_state=random_state
    )
    mapie_cal = TopLabelCalibrator(cv=cv)
    mapie_cal.fit(
        X=X_binary,
        y=y_binary,
        random_state=random_state
    )
    pred_ = mapie_cal.predict_proba(X_binary)
    top_label_ece_ = top_label_ece(y_binary, pred_)
    ece = expected_calibration_error(y_binary, pred_)
    np.testing.assert_array_almost_equal(
        np.array(results_binary[cv]["y_score"]),
        np.array(pred_),
        decimal=2
    )
    np.testing.assert_allclose(  # type:ignore
        results_binary[cv]["top_label_ece"],
        top_label_ece_,
        rtol=1e-2
    )
    np.testing.assert_allclose(  # type:ignore
        results_binary[cv]["ece"],
        ece,
        rtol=1e-2
    )


def test_different_binary_y_combinations() -> None:
    """
    Test that despite the different maximum in y value, the
    scores are always the same.
    """
    X_comb, y_comb = make_classification(
        n_samples=20,
        n_classes=3,
        n_informative=4,
        random_state=random_state
    )
    mapie_cal = TopLabelCalibrator()
    mapie_cal.fit(X_comb, y_comb, random_state=random_state)
    y_score = mapie_cal.predict_proba(X_comb)

    y_comb1 = np.where(y_comb == 2, 3, y_comb)
    mapie_cal1 = TopLabelCalibrator()
    mapie_cal1.fit(X_comb, y_comb1, random_state=random_state)
    y_score1 = mapie_cal1.predict_proba(X_comb)

    y_comb2 = np.where(y_comb == 2, 40, y_comb)
    mapie_cal2 = TopLabelCalibrator()
    mapie_cal2.fit(X_comb, y_comb2, random_state=random_state)
    y_score2 = mapie_cal2.predict_proba(X_comb)
    np.testing.assert_array_almost_equal(y_score, y_score1)
    np.testing.assert_array_almost_equal(y_score, y_score2)
    assert top_label_ece(
        y_comb, y_score, classes=mapie_cal.classes_
    ) == top_label_ece(
        y_comb1, y_score1, classes=mapie_cal1.classes_
    )
    assert top_label_ece(
        y_comb, y_score, classes=mapie_cal.classes_
    ) == top_label_ece(
        y_comb2, y_score2, classes=mapie_cal2.classes_
    )


@pytest.mark.parametrize(
    "calibrator", [LinearRegression(), "isotonic"]
)
def test_results_with_constant_sample_weights(
    calibrator: Union[str, RegressorMixin]
) -> None:
    """
    Test predictions when sample weights are None
    or constant with different values.

    Note that the calibration implementations from sklearn `calibration.py`
    file would not pass these tests.
    """
    n_samples = len(X)
    estimator = RandomForestClassifier(random_state=random_state)
    mapie_clf0 = TopLabelCalibrator(estimator=estimator, calibrator=calibrator)
    mapie_clf1 = TopLabelCalibrator(estimator=estimator, calibrator=calibrator)
    mapie_clf2 = TopLabelCalibrator(estimator=estimator, calibrator=calibrator)
    mapie_clf0.fit(X, y, sample_weight=None, random_state=random_state)
    mapie_clf1.fit(
        X, y, sample_weight=np.ones(shape=n_samples),
        random_state=random_state
    )
    mapie_clf2.fit(
        X, y, sample_weight=np.ones(shape=n_samples) * 5,
        random_state=random_state
    )
    y_pred0 = mapie_clf0.predict_proba(X)
    y_pred1 = mapie_clf1.predict_proba(X)
    y_pred2 = mapie_clf2.predict_proba(X)
    np.testing.assert_allclose(y_pred0, y_pred1)
    np.testing.assert_allclose(y_pred0, y_pred2)


def test_pipeline_compatibility() -> None:
    """Check that MAPIE works on pipeline based on pandas dataframes"""
    X = pd.DataFrame(
        {
            "x_cat": ["A", "A", "B", "A", "A", "B"],
            "x_num": [0, 1, 1, 4, np.nan, 5],
        }
    )
    y = pd.Series([0, 1, 2, 0, 1, 0])
    numeric_preprocessor = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="mean")),
        ]
    )
    categorical_preprocessor = Pipeline(
        steps=[
            ("encoding", OneHotEncoder(handle_unknown="ignore"))
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("cat", categorical_preprocessor, ["x_cat"]),
            ("num", numeric_preprocessor, ["x_num"])
        ]
    )
    pipe = make_pipeline(preprocessor, LogisticRegression())
    pipe.fit(X, y)
    mapie = TopLabelCalibrator(estimator=pipe)
    mapie.fit(X, y)
    mapie.predict(X)


def test_fit_parameters_passing() -> None:
    """
    Test passing fit parameters, here early stopping at iteration 3.
    Checks that underlying GradientBoosting estimators have used 3 iterations
    only during boosting, instead of default value for n_estimators (=100).
    """
    gb = GradientBoostingClassifier(random_state=random_state)

    mapie = TopLabelCalibrator(estimator=gb)

    def early_stopping_monitor(i, est, locals):
        """Returns True on the 3rd iteration."""
        if i == 2:
            return True
        else:
            return False

    mapie.fit(X, y, monitor=early_stopping_monitor)

    assert mapie.single_estimator_.estimators_.shape[0] == 3


def test_venn_abers_initialized() -> None:
    """Test that VennABERSCalibrator initialization does not crash."""
    VennABERSCalibrator()


def test_venn_abers_default_parameters() -> None:
    """Test default values of VennABERSCalibrator input parameters."""
    calibrator = VennABERSCalibrator()
    assert calibrator.estimator is None
    assert calibrator.cv == "split"


def test_venn_abers_prefit_cv_argument() -> None:
    """Test that prefit method works with VennABERSCalibrator"""
    # Create binary classification data
    X_binary, y_binary = make_classification(
        n_samples=100, n_features=4, n_classes=2, random_state=random_state
    )
    est = LogisticRegression().fit(X_binary, y_binary)
    calibrator = VennABERSCalibrator(estimator=est, cv="prefit")
    calibrator.fit(X_binary, y_binary)


def test_venn_abers_split_cv_argument() -> None:
    """Test that split method works with VennABERSCalibrator"""
    # Create binary classification data
    X_binary, y_binary = make_classification(
        n_samples=100, n_features=4, n_classes=2, random_state=random_state
    )
    calibrator = VennABERSCalibrator(cv="split")
    calibrator.fit(X_binary, y_binary)


@pytest.mark.parametrize("cv", ["noprefit", "nosplit"])
def test_venn_abers_invalid_cv_argument(cv: str) -> None:
    """Test that other cv method does not work with VennABERSCalibrator"""
    # Create binary classification data
    X_binary, y_binary = make_classification(
        n_samples=100, n_features=4, n_classes=2, random_state=random_state
    )
    with pytest.raises(
        ValueError,
        match=r".*Invalid cv argument.*",
    ):
        calibrator = VennABERSCalibrator(cv=cv)
        calibrator.fit(X_binary, y_binary)


def test_venn_abers_binary_classification() -> None:
    """Test VennABERSCalibrator on binary classification problem"""
    X_binary, y_binary = make_classification(
        n_samples=100, n_features=4, n_classes=2, random_state=random_state
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X_binary, y_binary, test_size=0.33, random_state=random_state
    )

    model = LogisticRegression().fit(X_train, y_train)
    calibrator = VennABERSCalibrator(estimator=model, cv="prefit")
    calibrator.fit(X_test, y_test)

    # Check that predict_proba returns probabilities
    probs = calibrator.predict_proba(X_test)
    assert probs.shape == (len(X_test), 2)
    assert np.all((0 <= probs) & (probs <= 1))
    assert np.allclose(np.sum(probs, axis=1), 1.0)

    # Check that predict returns class labels
    preds = calibrator.predict(X_test)
    assert preds.shape == (len(X_test),)
    assert set(np.unique(preds)).issubset(set(np.unique(y_binary)))


def test_venn_abers_prefit_split_same_results() -> None:
    """Test that prefit and split method
    return similar results for VennABERSCalibrator"""
    X_binary, y_binary = make_classification(
        n_samples=100, n_features=4, n_classes=2, random_state=random_state
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X_binary, y_binary, test_size=0.33, random_state=random_state
    )
    X_calib, X_test_final, y_calib, y_test_final = train_test_split(
        X_test, y_test, test_size=0.5, random_state=random_state
    )

    est = LogisticRegression(random_state=random_state).fit(X_train, y_train)

    # Prefit method
    calibrator_prefit = VennABERSCalibrator(estimator=est, cv="prefit")
    calibrator_prefit.fit(X_calib, y_calib)

    # Split method
    X_combined = np.vstack([X_train, X_calib])
    y_combined = np.hstack([y_train, y_calib])
    calibrator_split = VennABERSCalibrator(
        estimator=LogisticRegression(random_state=random_state)
    )
    calibrator_split.fit(X_combined, y_combined, random_state=random_state)

    # Compare results - note that we don't expect exact equality due to
    # the different calibration points used in each method
    y_prefit = calibrator_prefit.predict_proba(X_test_final)
    y_split = calibrator_split.predict_proba(X_test_final)

    # Check that predictions are at least correlated
    assert np.corrcoef(y_prefit[:, 1], y_split[:, 1])[0, 1] > 0.5


def test_venn_abers_calibration_effect() -> None:
    """Test that VennABERSCalibrator changes the probability estimates"""
    X_binary, y_binary = make_classification(
        n_samples=200, n_features=4, n_classes=2, random_state=random_state
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X_binary, y_binary, test_size=0.5, random_state=random_state
    )

    # Train a model
    model = LogisticRegression(random_state=random_state).fit(X_train, y_train)

    # Get uncalibrated probabilities
    uncalibrated_probs = model.predict_proba(X_test)

    # Apply Venn-ABERS calibration
    calibrator = VennABERSCalibrator(estimator=model, cv="prefit")
    calibrator.fit(X_train, y_train)  # Use training data for calibration

    # Get calibrated probabilities
    calibrated_probs = calibrator.predict_proba(X_test)

    # Check that calibration changes the probabilities
    assert not np.allclose(uncalibrated_probs, calibrated_probs)


def test_venn_abers_with_pipeline() -> None:
    """Check that VennABERSCalibrator works with sklearn pipeline"""
    X = pd.DataFrame({
        "x_cat": ["A", "A", "B", "A", "A", "B"] * 10,
        "x_num": [0, 1, 1, 4, 2, 5] * 10,
    })
    y = pd.Series([0, 1, 0, 1, 0, 1] * 10)

    numeric_preprocessor = Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
    ])
    categorical_preprocessor = Pipeline(steps=[
        ("encoding", OneHotEncoder(handle_unknown="ignore"))
    ])
    preprocessor = ColumnTransformer([
        ("cat", categorical_preprocessor, ["x_cat"]),
        ("num", numeric_preprocessor, ["x_num"])
    ])
    pipe = make_pipeline(preprocessor, LogisticRegression())
    pipe.fit(X, y)

    calibrator = VennABERSCalibrator(estimator=pipe)
    calibrator.fit(X, y)

    # Check predictions
    probs = calibrator.predict_proba(X)
    assert probs.shape == (len(X), 2)
    assert np.all((0 <= probs) & (probs <= 1))

    preds = calibrator.predict(X)
    assert preds.shape == (len(X),)
    assert set(np.unique(preds)).issubset(set(np.unique(y)))


def test_venn_abers_multiclass_error() -> None:
    """Test that VennABERSCalibrator raises error for multiclass problems"""
    calibrator = VennABERSCalibrator()

    with pytest.raises(
        ValueError,
        match=r".*Make sure to have one of the allowed targets:*"
    ):
        calibrator.fit(X, y)
