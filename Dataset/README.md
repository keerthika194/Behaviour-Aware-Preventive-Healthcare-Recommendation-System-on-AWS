# Diabetes Health Indicators Dataset (BRFSS 2015)

## Overview

This project uses the **Diabetes Health Indicators Dataset (BRFSS 2015)** to train and evaluate the preventive health risk prediction model.

The dataset is derived from the **Behavioral Risk Factor Surveillance System (BRFSS) 2015**, a nationwide health-related telephone survey conducted annually by the **Centers for Disease Control and Prevention (CDC)**. It contains demographic, lifestyle, and health-related indicators that are commonly associated with diabetes risk.

---

## Dataset Information

| Attribute | Details |
|-----------|---------|
| **Dataset Name** | Diabetes Health Indicators Dataset (BRFSS 2015) |
| **Source** | Centers for Disease Control and Prevention (CDC) – Behavioral Risk Factor Surveillance System (BRFSS) |
| **Platform** | Kaggle |
| **Records** | Approximately 253,680 |
| **Balanced Dataset** | 70,692 records (available separately) |
| **Features** | 21 lifestyle and health indicator attributes |
| **Target Variable** | `Diabetes_binary` |
| **Data Format** | CSV |
| **Data Type** | Structured / Tabular |
| **License** | CC0 – Public Domain |

---

## Features Included

The dataset contains various lifestyle and health-related attributes, including:

- High Blood Pressure
- High Cholesterol
- Cholesterol Check
- Body Mass Index (BMI)
- Smoking Status
- Stroke History
- Heart Disease or Heart Attack
- Physical Activity
- Fruit Consumption
- Vegetable Consumption
- Heavy Alcohol Consumption
- Healthcare Access
- General Health
- Mental Health
- Physical Health
- Difficulty Walking
- Biological Sex
- Age Group
- Education Level
- Income Level

**Target Variable**

- `Diabetes_binary`
  - **0** – No Diabetes
  - **1** – Diabetes

---

## Data Preprocessing

Before training the machine learning model, the dataset undergoes the following preprocessing steps:

- Data cleaning
- Handling missing or inconsistent values
- Feature selection
- Class balancing (where required)
- Data normalization and scaling
- Train-test split

---

## Usage in This Project

The dataset is used to:

- Train the XGBoost risk prediction model.
- Predict preventive health risk based on user lifestyle.
- Generate inputs for the behavioural adherence prediction module.
- Produce personalised recommendations using Generative AI.

---

## Original Dataset

The dataset is publicly available on Kaggle:

**Kaggle Link**

https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset

---

## Citation

Alex Teboul. *Diabetes Health Indicators Dataset (BRFSS 2015)*. Kaggle.

Original data source: Centers for Disease Control and Prevention (CDC), Behavioral Risk Factor Surveillance System (BRFSS) 2015.