"""
Homework #2 - Predicting Elastic Modulus (E) from Indentation Data with an ANN
                + Feature Importance analysis (Permutation Importance & SHAP)
==============================================================================
Pipeline mirrors the original notebook (20260617Training.ipynb) but:
  - target_column is changed from "YS" to "E"
  - adds test-set metrics (MAPE, MAE, RMSE)
  - adds Permutation Importance and SHAP to find which input features
    most influence the E prediction.
The focus of the last part is INTERPRETATION, not a perfect implementation.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping

# reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

HERE = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. Settings
# ============================================================
csv_path = os.path.join(HERE, "Trainingdata.csv")
target_column = "E"                      # <-- changed from "YS" to "E"
feature_columns = [
    "Pmax", "Stiffness2", "Slope1", "Slope2", "Slope3", "Slope4", "Slope5",
    "30um", "60um", "90um", "120um", "150um",
]

train_ratio, val_ratio, test_ratio = 0.7, 0.15, 0.15
epochs = 600
early_stopping_patience = 80
batch_size = 32
learning_rate = 1e-3
l2_lambda = 1e-4
dropout_rate = 0.2

# ============================================================
# 2. Load data
# ============================================================
df = pd.read_csv(csv_path)
print("Data shape:", df.shape)
X = df[feature_columns].values.astype("float32")
y = df[target_column].values.reshape(-1, 1).astype("float32")

# ============================================================
# 3. Split 70 / 15 / 15
# ============================================================
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, train_size=train_ratio, random_state=SEED, shuffle=True)
val_adj = val_ratio / (val_ratio + test_ratio)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, train_size=val_adj, random_state=SEED, shuffle=True)
print("Train:", X_train.shape, " Val:", X_val.shape, " Test:", X_test.shape)

# ============================================================
# 4. Min-Max scaling (fit on train only)
# ============================================================
scaler_X = MinMaxScaler()
X_train_s = scaler_X.fit_transform(X_train)
X_val_s = scaler_X.transform(X_val)
X_test_s = scaler_X.transform(X_test)


# ============================================================
# 5. MAPE loss
# ============================================================
def mape_loss(y_true, y_pred):
    eps = tf.keras.backend.epsilon()
    return tf.reduce_mean(
        tf.abs((y_true - y_pred) / tf.maximum(tf.abs(y_true), eps))) * 100.0


# ============================================================
# 6. Model (same architecture as original)
# ============================================================
model = Sequential([
    Dense(128, activation="relu", input_shape=(X_train_s.shape[1],),
          kernel_regularizer=l2(l2_lambda)),
    Dense(128, activation="relu", kernel_regularizer=l2(l2_lambda)),
    Dropout(dropout_rate),
    Dense(64, activation="relu", kernel_regularizer=l2(l2_lambda)),
    Dense(32, activation="relu", kernel_regularizer=l2(l2_lambda)),
    Dense(1),
])
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
              loss=mape_loss, metrics=[mape_loss])

early_stop = EarlyStopping(monitor="val_loss", patience=early_stopping_patience,
                           restore_best_weights=True, verbose=0)

history = model.fit(X_train_s, y_train, validation_data=(X_val_s, y_val),
                    epochs=epochs, batch_size=batch_size,
                    callbacks=[early_stop], verbose=0)
print(f"Trained for {len(history.history['loss'])} epochs (early stopping).")


# ============================================================
# 7. Test metrics: MAPE, MAE, RMSE
# ============================================================
y_pred = model.predict(X_test_s, verbose=0).flatten()
y_ref = y_test.flatten()

mape = np.mean(np.abs((y_ref - y_pred) / y_ref)) * 100
mae = np.mean(np.abs(y_ref - y_pred))
rmse = np.sqrt(np.mean((y_ref - y_pred) ** 2))
print("\n=== Test performance (Target: E) ===")
print(f"MAPE : {mape:6.3f} %")
print(f"MAE  : {mae:6.3f} GPa")
print(f"RMSE : {rmse:6.3f} GPa")

# ---- MAPE curve ----
plt.figure(figsize=(8, 5))
plt.plot(history.history["loss"], label="Training MAPE")
plt.plot(history.history["val_loss"], label="Validation MAPE")
plt.xlabel("Epoch"); plt.ylabel("MAPE (%)")
plt.title("MAPE Curve - Target: E")
plt.legend(); plt.grid(True)
plt.tight_layout(); plt.savefig(os.path.join(HERE, "E_mape_curve.png"), dpi=130)
plt.close()

# ---- Reference vs Prediction ----
plt.figure(figsize=(6, 6))
plt.scatter(y_ref, y_pred, s=10, alpha=0.6)
lo, hi = min(y_ref.min(), y_pred.min()), max(y_ref.max(), y_pred.max())
plt.plot([lo, hi], [lo, hi], "--", label="Ideal: Prediction = Reference")
plt.xlabel("Reference E"); plt.ylabel("Model Prediction E")
plt.title("Reference vs Prediction - Target: E")
plt.legend(); plt.grid(True); plt.axis("equal")
plt.tight_layout(); plt.savefig(os.path.join(HERE, "E_reference_vs_prediction.png"), dpi=130)
plt.close()


# ============================================================
# 8. Permutation Importance
#    Shuffle one feature at a time in the test set and measure how much
#    the test MAPE increases.  Bigger increase => more important feature.
# ============================================================
def test_mape(Xs):
    p = model.predict(Xs, verbose=0).flatten()
    return np.mean(np.abs((y_ref - p) / y_ref)) * 100

baseline = test_mape(X_test_s)
n_repeats = 20
rng = np.random.default_rng(SEED)
perm_imp = np.zeros(len(feature_columns))
perm_std = np.zeros(len(feature_columns))

for j in range(len(feature_columns)):
    deltas = []
    for _ in range(n_repeats):
        Xp = X_test_s.copy()
        rng.shuffle(Xp[:, j])                 # permute column j
        deltas.append(test_mape(Xp) - baseline)
    perm_imp[j] = np.mean(deltas)
    perm_std[j] = np.std(deltas)

order = np.argsort(perm_imp)
print("\n=== Permutation Importance (increase in test MAPE, %) ===")
for j in order[::-1]:
    print(f"{feature_columns[j]:>11}: {perm_imp[j]:7.3f}  (+/- {perm_std[j]:.3f})")

plt.figure(figsize=(8, 6))
plt.barh([feature_columns[j] for j in order],
         [perm_imp[j] for j in order],
         xerr=[perm_std[j] for j in order], color="#4C72B0")
plt.xlabel("Increase in Test MAPE when feature is shuffled (%)")
plt.title("Permutation Importance - Target: E")
plt.grid(True, axis="x", alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(HERE, "E_permutation_importance.png"), dpi=140)
plt.close()


# ============================================================
# 9. SHAP (model-agnostic), interpretation-focused
# ============================================================
try:
    import shap
    bg = shap.utils.sample(X_train_s, 100, random_state=SEED)   # background
    Xexp = shap.utils.sample(X_test_s, 200, random_state=SEED)  # explain subset
    f = lambda data: model.predict(data, verbose=0).flatten()
    explainer = shap.KernelExplainer(f, bg)
    shap_values = explainer.shap_values(Xexp, nsamples=100)
    shap_values = np.array(shap_values).reshape(Xexp.shape)

    mean_abs = np.mean(np.abs(shap_values), axis=0)
    sorder = np.argsort(mean_abs)
    print("\n=== SHAP mean(|value|) per feature (GPa) ===")
    for j in sorder[::-1]:
        print(f"{feature_columns[j]:>11}: {mean_abs[j]:7.3f}")

    plt.figure(figsize=(8, 6))
    plt.barh([feature_columns[j] for j in sorder],
             [mean_abs[j] for j in sorder], color="#DD8452")
    plt.xlabel("mean(|SHAP value|)  ->  average impact on E prediction (GPa)")
    plt.title("SHAP Feature Importance - Target: E")
    plt.grid(True, axis="x", alpha=0.3)
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "E_shap_importance.png"), dpi=140)
    plt.close()
    print("Saved: E_shap_importance.png")
except Exception as e:
    print("\n[SHAP skipped due to:]", repr(e))

print("\nSaved figures: E_mape_curve.png, E_reference_vs_prediction.png, "
      "E_permutation_importance.png")
