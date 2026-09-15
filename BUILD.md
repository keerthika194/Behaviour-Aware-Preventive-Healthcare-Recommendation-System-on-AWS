# Build and Run Instructions

This document provides step-by-step instructions for running the **Behaviour Aware Preventive Healthcare Recommendation System** locally.

Since the heavy lifting of the backend is fully serverless and deployed to **AWS (API Gateway, Lambda, DynamoDB, IoT Core)**, you do not need to run a local database or backend API server. You only need to run the **Frontend Application**, the **IoT Smartwatch Simulator**, and the **Local ML Pipeline** (to process new events).

---

## 1. Prerequisites

*   **Node.js** (v18+ recommended) and `npm` installed.
*   **Python 3.11+** installed.
*   **AWS CLI** configured locally with an IAM user that has DynamoDB read/write permissions for the project tables.

---

## 2. Environment Configuration

Because the repository is securely stripped of personal credentials, you must create `.env` files in your local environments.

### Frontend Environment
Navigate to `frontend/` and copy the example environment file:
```bash
cd frontend
cp .env.example .env
```
Ensure your `.env` contains the correct AWS variables:
```
VITE_API_BASE_URL=https://<your-api-id>.execute-api.<region>.amazonaws.com
VITE_COGNITO_USER_POOL_ID=<your-user-pool-id>
VITE_COGNITO_CLIENT_ID=<your-client-id>
```

### IoT Simulator Environment
Navigate to `iot_simulator/`, ensure your AWS IoT certificates are placed inside `iot_simulator/certs/`, and create the `.env` file:
```bash
cd iot_simulator
cp .env.example .env
```
Ensure your `.env` contains your specific AWS IoT endpoint and certificate paths.

---

## 3. Starting the System

To see the end-to-end data flow locally, you'll need to run three components. We recommend opening three separate terminal windows.

### Terminal 1: Start the React Frontend Dashboard
This serves the web application on `http://localhost:3000`.
```bash
cd frontend
npm install
npm run dev
```

### Terminal 2: Start the IoT Watch Simulator
This simulates smartwatch activity data and streams the payloads to AWS IoT Core.
```bash
cd iot_simulator
pip install -r requirements.txt
python watch_simulator.py --user <your-cognito-sub-id>
```
*(Passing the `--user` flag ensures the simulator links the telemetry data directly to your authenticated user account in the database).*

### Terminal 3: Run the ML Processing Pipeline
The ML pipeline is a discrete script. It retrieves the latest telemetry events from DynamoDB, calculates the Activity classification and Disease Risk scores, generates recommendations via Generative AI, and pushes the final records back to DynamoDB.
```bash
# Ensure you are in the project root
python backend/ml_service.py --user <your-cognito-sub-id>
```
*(Note: As long as the script executes successfully without AWS AccessDenied exceptions, the dashboard in Terminal 1 will automatically refresh to show your new risk assessment and personalized recommendations!)*

---

## 4. Verification

1.  Open `http://localhost:3000` and sign in (or sign up) using your Cognito user pool account.
2.  Navigate to the **Profile** tab, fill out your health indicators (like BMI, Physical Activity, Age), and click **Save Profile**.
3.  Ensure your IoT simulator (Terminal 2) has sent at least one recent payload.
4.  Run the ML Pipeline (Terminal 3).
5.  Return to the web dashboard and you will see the updated "Today's Behaviour", your new "Preventive Risk" score, and custom Generative AI recommendations tailored to your exact behavior profile.
