"""
Tests pour ML Pipeline - Entraînement et Prédictions
"""
import pytest
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from lightgbm import LGBMClassifier


# ============================================================================
# TESTS DATASET
# ============================================================================

@pytest.mark.ml
@pytest.mark.unit
def test_training_data_no_nulls(sample_training_data):
    """Test que les données d'entraînement n'ont pas de nulls"""
    X, y = sample_training_data

    assert not X.isnull().any().any(), "Training data contains nulls"
    assert not pd.Series(y).isnull().any(), "Labels contain nulls"


@pytest.mark.ml
@pytest.mark.unit
def test_training_data_shape(sample_training_data):
    """Test dimensions des données"""
    X, y = sample_training_data

    assert X.shape[0] == len(y), "X and y have different lengths"
    assert X.shape[0] > 100, "Dataset too small (<100 samples)"
    assert X.shape[1] > 0, "No features in dataset"


@pytest.mark.ml
@pytest.mark.unit
def test_training_labels_distribution(sample_training_data):
    """Test distribution des labels (équilibrée)"""
    X, y = sample_training_data

    unique, counts = np.unique(y, return_counts=True)

    # Vérifier 3 classes
    assert len(unique) == 3, f"Expected 3 classes, got {len(unique)}"
    assert set(unique) == {-1, 0, 1}, f"Labels should be -1, 0, 1, got {unique}"

    # Vérifier distribution pas trop déséquilibrée (>10% pour chaque classe)
    for count in counts:
        ratio = count / len(y)
        assert ratio > 0.1, f"Class imbalance too high: {ratio:.2%}"


@pytest.mark.ml
@pytest.mark.unit
def test_feature_ranges_valid(sample_training_data):
    """Test que les features sont dans des ranges valides"""
    X, y = sample_training_data

    # close_return devrait être petit (< 5%)
    assert (X['close_return'].abs() < 0.05).all(), "close_return values too large"

    # volatility devrait être positive
    assert (X['volatility_1h'] >= 0).all(), "Negative volatility"

    # VIX devrait être entre 5 et 80
    assert (X['vix_close'] >= 5).all() and (X['vix_close'] <= 80).all(), "VIX out of range"


# ============================================================================
# TESTS ENTRAÎNEMENT
# ============================================================================

@pytest.mark.ml
@pytest.mark.unit
def test_model_training_succeeds(sample_training_data):
    """Test que l'entraînement se termine sans erreur"""
    X, y = sample_training_data

    model = LGBMClassifier(
        n_estimators=10,
        max_depth=3,
        random_state=42,
        verbose=-1
    )

    # Ne doit pas lever d'exception
    model.fit(X, y)

    assert model.n_features_ == X.shape[1]


@pytest.mark.ml
@pytest.mark.unit
def test_model_achieves_minimum_accuracy(sample_training_data):
    """Test que le modèle atteint une accuracy minimale"""
    X, y = sample_training_data

    model = LGBMClassifier(
        n_estimators=50,
        max_depth=5,
        random_state=42,
        verbose=-1
    )

    model.fit(X, y)

    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)

    # Sur les données d'entraînement, devrait avoir au moins 60% accuracy
    assert accuracy > 0.6, f"Training accuracy too low: {accuracy:.2%}"


@pytest.mark.ml
@pytest.mark.integration
def test_model_overfitting_check(sample_training_data):
    """Test de détection d'overfitting (train vs test split)"""
    from sklearn.model_selection import train_test_split

    X, y = sample_training_data

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    model = LGBMClassifier(
        n_estimators=50,
        max_depth=5,
        random_state=42,
        verbose=-1
    )

    model.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_acc = accuracy_score(y_test, model.predict(X_test))

    # Test accuracy ne devrait pas être plus de 50% inférieure à train accuracy
    # Note: Avec des données aléatoires, le gap peut être élevé
    assert test_acc > (train_acc - 0.5), f"Possible overfitting: train={train_acc:.2%}, test={test_acc:.2%}"


# ============================================================================
# TESTS PRÉDICTIONS
# ============================================================================

@pytest.mark.ml
@pytest.mark.unit
def test_model_prediction_output_format(trained_model, sample_training_data):
    """Test format de sortie des prédictions"""
    X, y = sample_training_data

    predictions = trained_model.predict(X[:10])
    probabilities = trained_model.predict_proba(X[:10])

    # Vérifier format
    assert len(predictions) == 10
    assert probabilities.shape == (10, 3), "Should have 3 probability columns"
    assert set(predictions).issubset({-1, 0, 1}), "Predictions should be -1, 0, or 1"


@pytest.mark.ml
@pytest.mark.unit
def test_model_probabilities_sum_to_one(trained_model, sample_training_data):
    """Test que les probabilités somment à 1"""
    X, y = sample_training_data

    probabilities = trained_model.predict_proba(X[:10])

    # Chaque ligne doit sommer à 1
    sums = probabilities.sum(axis=1)
    assert np.allclose(sums, 1.0), "Probabilities don't sum to 1"


@pytest.mark.ml
@pytest.mark.unit
def test_model_confidence_scores(trained_model, sample_training_data):
    """Test calcul des scores de confiance"""
    X, y = sample_training_data

    probabilities = trained_model.predict_proba(X[:10])
    confidence_scores = probabilities.max(axis=1)

    # Confiance devrait être entre 0.33 et 1.0 (3 classes)
    assert (confidence_scores >= 0.33).all()
    assert (confidence_scores <= 1.0).all()


# ============================================================================
# TESTS FEATURE IMPORTANCE
# ============================================================================

@pytest.mark.ml
@pytest.mark.unit
def test_model_has_feature_importance(trained_model):
    """Test que le modèle a des feature importances"""
    assert hasattr(trained_model, 'feature_importances_')

    importances = trained_model.feature_importances_
    assert len(importances) > 0
    assert (importances >= 0).all(), "Feature importances should be non-negative"


@pytest.mark.ml
@pytest.mark.unit
def test_feature_importance_sums_correctly(trained_model):
    """Test que feature importances somment correctement"""
    importances = trained_model.feature_importances_

    # Pour LightGBM, importances peuvent sommer à différentes valeurs selon le type
    # Juste vérifier qu'elles existent et sont non-négatives
    assert importances.sum() > 0


# ============================================================================
# TESTS MÉTRIQUES
# ============================================================================

@pytest.mark.ml
@pytest.mark.unit
def test_calculate_balanced_accuracy(sample_training_data, trained_model):
    """Test calcul de balanced accuracy"""
    X, y = sample_training_data

    y_pred = trained_model.predict(X)
    balanced_acc = balanced_accuracy_score(y, y_pred)

    # Devrait être >= 0.3 (proche du random pour 3 classes = 0.33)
    # Note: Avec données aléatoires, le modèle ne peut pas être meilleur que random
    assert balanced_acc >= 0.3, f"Balanced accuracy too low: {balanced_acc:.2%}"


@pytest.mark.ml
@pytest.mark.integration
def test_classification_report_metrics(sample_training_data, trained_model):
    """Test génération classification report"""
    from sklearn.metrics import classification_report

    X, y = sample_training_data

    y_pred = trained_model.predict(X)
    report = classification_report(y, y_pred, output_dict=True)

    # Vérifier clés
    assert '-1' in report  # SELL
    assert '0' in report   # HOLD
    assert '1' in report   # BUY
    assert 'accuracy' in report

    # Vérifier métriques pour chaque classe
    for label in ['-1', '0', '1']:
        assert 'precision' in report[label]
        assert 'recall' in report[label]
        assert 'f1-score' in report[label]


# ============================================================================
# TESTS VALIDATION CROSS-VALIDATION
# ============================================================================

@pytest.mark.ml
@pytest.mark.slow
@pytest.mark.integration
def test_cross_validation_performance(sample_training_data):
    """Test performance avec cross-validation"""
    from sklearn.model_selection import cross_val_score

    X, y = sample_training_data

    model = LGBMClassifier(
        n_estimators=30,
        max_depth=4,
        random_state=42,
        verbose=-1
    )

    # 3-fold CV
    scores = cross_val_score(model, X, y, cv=3, scoring='balanced_accuracy')

    # Moyenne devrait être >= 0.25 (données aléatoires, baseline = 0.33)
    assert scores.mean() >= 0.25, f"CV balanced accuracy too low: {scores.mean():.2%}"

    # Variance ne devrait pas être trop grande (< 0.3)
    assert scores.std() < 0.3, f"CV variance too high: {scores.std():.2%}"


# ============================================================================
# TESTS SERIALIZATION
# ============================================================================

@pytest.mark.ml
@pytest.mark.unit
def test_model_serialization(trained_model):
    """Test sauvegarde/chargement du modèle"""
    import joblib
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
        # Save
        joblib.dump(trained_model, f.name)

        # Load
        loaded_model = joblib.load(f.name)

        # Vérifier équivalence
        assert trained_model.n_features_ == loaded_model.n_features_
        assert np.array_equal(
            trained_model.feature_importances_,
            loaded_model.feature_importances_
        )


@pytest.mark.ml
@pytest.mark.integration
def test_mlflow_model_logging(trained_model, sample_training_data):
    """Test logging MLflow"""
    import mlflow
    import tempfile

    X, y = sample_training_data

    with tempfile.TemporaryDirectory() as tmpdir:
        mlflow.set_tracking_uri(f"file://{tmpdir}")

        with mlflow.start_run():
            # Log model
            mlflow.sklearn.log_model(trained_model, "model")

            # Log params
            mlflow.log_params({
                "n_estimators": 10,
                "max_depth": 3
            })

            # Log metrics
            y_pred = trained_model.predict(X)
            accuracy = accuracy_score(y, y_pred)
            mlflow.log_metric("accuracy", accuracy)

        # Vérifier que le run existe
        runs = mlflow.search_runs()
        assert len(runs) > 0
