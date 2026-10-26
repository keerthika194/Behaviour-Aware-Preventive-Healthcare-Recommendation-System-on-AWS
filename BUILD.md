# Build and Run Instructions

This document provides step-by-step instructions for running the **Behaviour-Aware Preventive Healthcare Recommendation System** on any machine.

Since the backend is serverless and deployed to **AWS in `ap-south-1` (Mumbai)** across Amazon Cognito, Amazon API Gateway HTTP API v2, AWS IoT Core, AWS Lambda, and Amazon DynamoDB, you do not need to install local databases. You only need to run the **Frontend Application**, the **IoT Smartwatch Simulator**, and the **Decoupled Stream Runner / ML Engine**.

---

## Method 1: Instant Demonstration (No Setup Required)

If you just want to demo or evaluate the live application on another device (laptop, mobile phone, or tablet):
1. Open any modern web browser.
2. Navigate to the production AWS Amplify URL:  
   **[https://main.d13b5qy6zqsapl.amplifyapp.com](https://main.d13b5qy6zqsapl.amplifyapp.com)**
3. Sign in using existing credentials or click **Sign Up** to create a verified Cognito account.
4. Fill in the clinical survey in the **Profile** tab and view real-time risk gauges, live recognized physical states, and adaptive JITAI lifestyle recommendations.

---

## Method 2: Running the Project Locally on a New Device

### 1. Prerequisites
* **Git** installed.
* **Node.js** (v18.x or v20.x LTS) and `npm`.
* **Python** (v3.10 to v3.12).
* **AWS CLI** installed and configured (`aws configure`) with credentials having access to the project's DynamoDB tables (`profiles`, `activity_events`, `recommendations`) in region `ap-south-1`.

---

### 2. Clone the Repository
```bash
git clone https://github.com/keerthika194/Behaviour-Aware-Preventive-Healthcare-Recommendation-System-on-AWS.git
cd Behaviour-Aware-Preventive-Healthcare-Recommendation-System-on-AWS
```

---

### 3. Step-by-Step Setup

#### Terminal 1: Run the React 18 Frontend
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Verify or create `.env` (copy from `.env.example`):
   ```bash
   # On Windows:
   copy .env.example .env
   # On macOS/Linux:
   cp .env.example .env
   ```
   *The `.env` uses public AWS parameters:*
   ```ini
   VITE_AWS_REGION=ap-south-1
   VITE_COGNITO_USER_POOL_ID=ap-south-1_EtqP8T35c
   VITE_COGNITO_CLIENT_ID=8ubr2bs69koakql1cpl85nc5b
   VITE_API_BASE_URL=https://sofhfh3jm8.execute-api.ap-south-1.amazonaws.com
   ```
3. Install dependencies and start the Vite development server:
   ```bash
   npm install
   npm run dev
   ```
4. Open your browser at **`http://localhost:5173`**.

---

#### Terminal 2: Run the Smartwatch Telemetry Simulator
The simulator streams 20 Hz, 6-axis IMU (accelerometer + gyroscope) sensor data to AWS IoT Core over MQTT / TLS 1.3:
1. Navigate to `iot_simulator`:
   ```bash
   cd iot_simulator
   pip install -r requirements.txt
   ```
2. Ensure IoT certificates are present in `iot_simulator/certs/` and configure `iot_simulator/.env`:
   ```ini
   AWS_IOT_ENDPOINT=a3sssai20yw40p-ats.iot.ap-south-1.amazonaws.com
   AWS_IOT_CLIENT_ID=health-adherence-device
   AWS_IOT_CERT_PATH=certs/26781763086e5e900056e5e56045bff216c4fd297b30eb6ed73241042e3a072a-certificate.pem.crt
   AWS_IOT_PRIVATE_KEY_PATH=certs/26781763086e5e900056e5e56045bff216c4fd297b30eb6ed73241042e3a072a-private.pem.key
   AWS_IOT_ROOT_CA_PATH=certs/AmazonRootCA1.pem
   AWS_IOT_TOPIC=health-adherence/telemetry
   ```
3. Run the simulator (pass your Cognito User ID / Sub to link telemetry to your profile):
   ```bash
   python watch_simulator.py --user <your-cognito-user-id>
   ```

---

#### Terminal 3: Run the Decoupled ML Stream Runner
The stream runner acts as the operational daemon polling unprocessed events from DynamoDB `activity_events`, executing feature extraction (30 statistical metrics), dual ML inference (Random Forest + XGBoost), and writing recommendations with 24-hour TTL:
1. In the project root, create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
2. Install required packages:
   ```bash
   pip install boto3 scikit-learn xgboost joblib numpy pandas
   ```
3. Launch the stream runner daemon:
   ```bash
   python backend/runners/stream_runner.py
   ```
   *The runner will continuously process incoming events in real time and log inference metrics.*

---

### 4. Running the Automated Verification Suite
To verify that all machine learning models, feature extraction algorithms, DynamoDB Decimal handlers, and TTL expiration logic are 100% operational on the new device, run:
```bash
python scratch/test_ml_lambda.py
```
Expected result: **26 tests run, 26 passed (100% pass rate in ~3.5 seconds).**
