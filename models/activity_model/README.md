# Smartwatch Activity Recognition Model (Model 2)

This module implements **Model 2: Smartwatch Activity Recognition** using a Random Forest Classifier trained on sensor data from the WISDM Smartphone and Smartwatch dataset.

---

## 🎯 Purpose of the Model
In modern preventive healthcare systems, asking users to manually log their physical activities every day creates friction and inaccurate reports. This model automates activity tracking by reading continuous 10-second motion streams from a simulated smartwatch (IoT device) and classifying the user's real-time physical activity (e.g., *Walking*, *Sitting*, *Jogging*, *Stairs*, *Folding Clothes*).

---

## ⌚ WISDM Dataset & Sensor Selection
- **Dataset**: WISDM Smartphone and Smartwatch Activity and Biometrics Dataset (UCI Machine Learning Repository).
- **Sensors Used**: Smartwatch Accelerometer (3-axis: X, Y, Z) and Smartwatch Gyroscope (3-axis: X, Y, Z).
- **Why Accelerometer & Gyroscope?**:
  - **Accelerometer**: Measures linear acceleration and movement direction (e.g., detecting stride frequency during walking vs. sitting still).
  - **Gyroscope**: Measures angular velocity and wrist rotation (e.g., distinguishing between writing, drinking from a cup, or brushing teeth).

---

## 📊 30 Input Sensor Features
For every 10-second time window (sampled at 20 Hz = 200 raw readings per window), 5 statistical time-domain features are extracted across each of the 6 sensor axes ($3 \text{ Accel axes} + 3 \text{ Gyro axes} = 30 \text{ features}$):

1. **Mean**: Average motion magnitude along the axis.
2. **Standard Deviation (`std`)**: Motion intensity / variation.
3. **Minimum (`min`)**: Lowest recorded value.
4. **Maximum (`max`)**: Peak acceleration / rotation.
5. **Average Absolute Difference (`avg_abs_diff`)**: Rate of motion change.

*Note: `subject_id` is excluded during model training to ensure the model generalizes to new unseen users rather than memorizing individual user movement styles.*

---

## 🌲 Why Random Forest?
1. **Handles Non-Linearity & Multiclass Complexity**: Activity recognition involves 18 distinct movement classes with non-linear feature boundaries. Random Forest handles complex decision boundaries naturally.
2. **Robust Against Noise & Outliers**: Smartwatch motion streams contain natural noise (e.g., sudden arm twitches). Ensemble decision trees average predictions across 200 trees, reducing variance.
3. **High Efficiency for Cloud Deployment**: Fast inference times (<5 ms per window), making it lightweight for real-time execution inside AWS Functions.

---

## 🏃 Target Activity Classes (18 Total)
`Brushing_Teeth`, `Catch_Tennis_Ball`, `Clapping`, `Dribbling_Basketball`, `Drinking_from_Cup`, `Eating_Chips`, `Eating_Pasta`, `Eating_Sandwich`, `Eating_Soup`, `Folding_Clothes`, `Jogging`, `Kicking_Soccer_Ball`, `Sitting`, `Standing`, `Stairs`, `Typing`, `Walking`, `Writing`.

---

## 📈 Dataset Sizes & Metrics
- **Train Dataset Size**: 13,625 window samples (80%)
- **Test Dataset Size**: 3,407 window samples (20%)
- **Target Metrics**: Evaluated using weighted-average Accuracy, Precision, Recall, and F1-score across all 18 activity classes.

---

## 💾 Model Artifacts
- `activity_model.pkl`: Trained Scikit-Learn `RandomForestClassifier` serialized using `joblib`.
- `feature_schema.json`: Declares feature column names, order, hyperparameter config, and evaluation metrics.

---

## 🚀 How `predict_activity()` Works

```python
from inference import predict_activity

sample_sensor_window = {
    "acc_x_mean": 1.25, "acc_x_std": 0.45, "acc_x_min": -0.12, "acc_x_max": 2.10, "acc_x_avg_abs_diff": 0.35,
    "acc_y_mean": 9.81, "acc_y_std": 0.20, "acc_y_min": 9.10, "acc_y_max": 10.25, "acc_y_avg_abs_diff": 0.15,
    "acc_z_mean": 0.50, "acc_z_std": 0.30, "acc_z_min": -0.20, "acc_z_max": 1.10, "acc_z_avg_abs_diff": 0.22,
    "gyr_x_mean": 0.02, "gyr_x_std": 0.15, "gyr_x_min": -0.50, "gyr_x_max": 0.50, "gyr_x_avg_abs_diff": 0.10,
    "gyr_y_mean": 0.01, "gyr_y_std": 0.10, "gyr_y_min": -0.30, "gyr_y_max": 0.30, "gyr_y_avg_abs_diff": 0.08,
    "gyr_z_mean": 0.05, "gyr_z_std": 0.12, "gyr_z_min": -0.40, "gyr_z_max": 0.40, "gyr_z_avg_abs_diff": 0.09
}

result = predict_activity(sample_sensor_window)
print(result)
# Output:
# {
#   "activity": "Sitting",
#   "confidence": 0.985
# }
```

---

## 🔗 System Architecture Integration Blueprint

```
 ┌────────────────────────────────┐
 │ Simulated Smartwatch (IoT)     │  Generates 20 Hz Accel & Gyro stream
 └───────────────┬────────────────┘
                 │ (HTTP POST / Event Hub)
                 ▼
 ┌────────────────────────────────┐
 │ AWS Function (Activity App)  │  Calls predict_activity(sensor_features)
 └───────────────┬────────────────┘  Returns predicted activity (e.g. "Walking")
                 │
                 ▼
 ┌────────────────────────────────┐
 │ AWS Preventive Health Engine │  Combines:
 └────────────────────────────────┘   1. Long-term Risk Score (Model 1 - XGBoost)
                                      2. Daily Active Minutes (Model 2 - Random Forest)
                                      => Generates Personalized Health Recommendation!
```
