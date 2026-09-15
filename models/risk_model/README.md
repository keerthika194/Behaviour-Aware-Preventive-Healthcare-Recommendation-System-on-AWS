# Preventive Risk Prediction Model (Model 1)

This module implements **Model 1: Preventive Risk Prediction** using XGBoost on the CDC BRFSS 2015 dataset.

## Model Summary
- **Target**: `Diabetes_binary` (0.0 = No Diabetes, 1.0 = Diabetes/Prediabetes)
- **Model Architecture**: Extreme Gradient Boosting Classifier (`XGBoostClassifier`)
- **Dataset**: CDC BRFSS 2015 Diabetes Health Indicators (55,245 training records, 13,812 test records)
- **Primary Purpose**: Evaluates long-term chronic health and lifestyle risk to calculate a continuous risk probability score $p \in [0, 1]$ and map it to a actionable risk band (`Low`, `Medium`, `High`).

## Input Features (21 Total)
The model expects the following 21 features in exact numerical order:

| Feature | Description | Range / Values |
| :--- | :--- | :--- |
| `HighBP` | High blood pressure history | 0 = No, 1 = Yes |
| `HighChol` | High cholesterol history | 0 = No, 1 = Yes |
| `CholCheck` | Cholesterol check in past 5 years | 0 = No, 1 = Yes |
| `BMI` | Body Mass Index | Continuous (e.g., 28.5) |
| `Smoker` | Smoked >= 100 cigarettes in lifetime | 0 = No, 1 = Yes |
| `Stroke` | Ever told had a stroke | 0 = No, 1 = Yes |
| `HeartDiseaseorAttack` | Coronary heart disease or myocardial infarction | 0 = No, 1 = Yes |
| `PhysActivity` | Physical activity in past 30 days | 0 = No, 1 = Yes |
| `Fruits` | Consume fruit 1+ times per day | 0 = No, 1 = Yes |
| `Veggies` | Consume vegetables 1+ times per day | 0 = No, 1 = Yes |
| `HvyAlcoholConsump` | Heavy alcohol consumption | 0 = No, 1 = Yes |
| `AnyHealthcare` | Have any health care coverage | 0 = No, 1 = Yes |
| `NoDocbcCost` | Couldn't see doctor due to cost | 0 = No, 1 = Yes |
| `GenHlth` | General health rating | 1 (Excellent) to 5 (Poor) |
| `MentHlth` | Days of poor mental health (past 30 days) | 0 to 30 |
| `PhysHlth` | Days of poor physical health (past 30 days) | 0 to 30 |
| `DiffWalk` | Serious difficulty walking or climbing stairs | 0 = No, 1 = Yes |
| `Sex` | Gender | 0 = Female, 1 = Male |
| `Age` | Age category | 1 (18-24) to 13 (80+) |
| `Education` | Education level | 1 (Elementary) to 6 (College 4+ yrs) |
| `Income` | Annual household income category | 1 (<$10k) to 8 (>$75k) |

## Risk Band Threshold Rationale
Probability score $p = P(\text{Diabetes\_binary} = 1)$ is categorized into three clinical bands:

- **Low Risk** ($p < 0.35$): Low overall risk. Recommend standard healthy lifestyle upkeep.
- **Medium Risk** ($0.35 \le p < 0.65$): Moderate risk profile. Targeted behavioral interventions (dietary improvement, increased activity) recommended.
- **High Risk** ($p \ge 0.65$): High risk profile. Urgent preventive health advisory and medical evaluation recommended.

## Model Training & Artifacts
To train or re-tune the model:
```bash
python train_risk_model.py
```

Generated artifacts:
- `risk_model.json`: Native XGBoost model file.
- `feature_schema.json`: Schema file declaring input feature ordering, best hyperparameters, and test evaluation metrics.

## How Inference Works
Import `predict_risk` from `inference.py`:

```python
from inference import predict_risk

input_data = {
    "HighBP": 1,
    "HighChol": 1,
    "CholCheck": 1,
    "BMI": 30.5,
    "Smoker": 0,
    "Stroke": 0,
    "HeartDiseaseorAttack": 0,
    "PhysActivity": 1,
    "Fruits": 1,
    "Veggies": 1,
    "HvyAlcoholConsump": 0,
    "AnyHealthcare": 1,
    "NoDocbcCost": 0,
    "GenHlth": 3,
    "MentHlth": 2,
    "PhysHlth": 4,
    "DiffWalk": 0,
    "Sex": 1,
    "Age": 8,
    "Education": 5,
    "Income": 6
}

result = predict_risk(input_data)
print(result)
# Output:
# {
#   "score": 0.4215,
#   "band": "Medium",
#   "thresholds": {"low": "< 0.35", "medium": "0.35 - 0.65", "high": ">= 0.65"},
#   "missing_features_defaulted": []
# }
```
