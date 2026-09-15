# Behaviour Aware Preventive Healthcare Recommendation System on AWS

This project is an end-to-end, behavior-aware healthcare recommendation system built natively on AWS. It uses Machine Learning (XGBoost and Random Forest) alongside Generative AI (Llama 3.1) to not only predict lifestyle disease risks based on health indicators, but also incorporate real-time adherence modeling from simulated IoT smartwatch data. 

Unlike traditional healthcare platforms that give static advice, this system predicts how likely a user is to adhere to an intervention based on their real-time behavior (like sitting vs. exercising) and generates personalized, practical, and highly achievable recommendations.

## Key Features

*   **IoT Smartwatch Simulation**: Streams real-time activity metrics to AWS IoT Core.
*   **Dual Machine Learning Pipeline**:
    *   *Activity Recognition*: Classifies real-time behavior (e.g., Sitting, Walking) using a Random Forest model trained on WISDM sensor data.
    *   *Preventive Risk Prediction*: Predicts lifestyle disease risk (e.g., Diabetes) using an XGBoost model trained on CDC BRFSS 2015 data.
*   **Generative AI Recommendations**: Synthesizes the predicted risk score and current activity into actionable, personalized health advice.
*   **Serverless AWS Architecture**: Highly scalable and cost-effective backend utilizing API Gateway, Lambda, DynamoDB, and Cognito.
*   **Interactive React Dashboard**: A modern frontend (built with Vite + TypeScript + Tailwind) that authenticates via Cognito and visualizes risk indicators and real-time recommendations.

## AWS Architecture Overview

1.  **Authentication**: Users log in securely via **Amazon Cognito** (User Pool). The frontend receives a JWT ID token which is used to authorize all API requests.
2.  **API Layer**: **Amazon API Gateway** (HTTP API v2) acts as the secure entry point, verifying the Cognito JWT via a built-in Authorizer before forwarding requests to the backend.
3.  **Serverless Compute**: **AWS Lambda** handles all backend business logic:
    *   `health-adherence-profile`: Manages fetching and updating user health profile indicators.
    *   `health-adherence-processor`: Ingests and processes data from the IoT stream.
    *   `health-adherence-recommendation`: Integrates with the Generative AI (Groq API / Llama 3.1) to produce the final recommendations.
    *   `health-adherence-get-recommendations`: Serves the history of recommendations to the frontend.
4.  **Database**: **Amazon DynamoDB** serves as the NoSQL storage layer, maintaining separate tables for `profiles`, `activity_events`, `daily_aggregates`, and `recommendations`.
5.  **Data Ingestion**: **AWS IoT Core** receives telemetry data from the local python IoT Watch Simulator.

## Repository Structure

```
.
├── backend/            # AWS Lambda functions, deployment scripts, and ML prediction pipeline
├── frontend/           # React (Vite/TS/Tailwind) web application
├── iot_simulator/      # Python script to stream synthetic smartwatch data to AWS IoT Core
├── models/             # Trained ML models (XGBoost, Random Forest, Scalers)
├── datasets/           # Raw and processed datasets (BRFSS and WISDM)
├── infra/              # Infrastructure-as-code or deployment references
├── BUILD.md            # Step-by-step instructions for running the project locally
└── README.md           # This file
```

## Security Note

All sensitive keys, AWS credentials, certificates, and `.env` files are strictly omitted from this repository via `.gitignore` to ensure robust security. If you are deploying this project yourself, you will need to supply your own AWS Cognito, API Gateway, and IoT Core configurations.

## License
This project is licensed under the MIT License.
