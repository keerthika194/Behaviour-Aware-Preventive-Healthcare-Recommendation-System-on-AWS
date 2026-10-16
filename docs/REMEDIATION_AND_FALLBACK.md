# Serverless ML Engine: Cloud Provisioning Remediation & Development Fallback Guide

**Author:** Teamwork SWE Light Adversarial Reviewer & QA  
**Date:** October 16, 2026  
**Target AWS Region:** `ap-south-1` (Mumbai)  
**Target Function:** `health-adherence-ml-engine`  
**Target Stream:** DynamoDB `activity_events` (`NEW_IMAGE`)  
**Target User Identity:** `arn:aws:iam::751605536502:user/health-adherence-local`  

---

## 1. Executive Summary & Root Cause Analysis

### 1.1 Architectural Target: Pattern B (Decoupled DynamoDB Streams)
The Health Adherence architecture uses **Pattern B: Decoupled DynamoDB Streams** to run serverless dual machine learning inference without introducing synchronous latency to sensor ingestion:
1. Smartwatch sensor telemetry streams into **AWS IoT Core** at 20 Hz (200 readings per 10-second window).
2. Raw records are persisted into DynamoDB `activity_events` with `status: "received"`.
3. DynamoDB Streams (`NEW_IMAGE`) triggers the `health-adherence-ml-engine` Lambda function (batch size 1–5).
4. The Lambda function extracts 30 statistical time-domain features, retrieves the user's clinical baseline from `profiles`, executes dual inference (Random Forest activity classifier + XGBoost chronic risk classifier), writes a JITAI intervention to `recommendations` with a 24-hour Unix epoch TTL (`expire_at`), and marks the source event as `processed`.

```
[IoT Smartwatch]
       │
       ▼ (MQTT 20Hz)
[AWS IoT Core]
       │
       ▼ (Rule Ingestion)
[DynamoDB: activity_events] (status='received')
       │
       ├──► [Path A: Production Cloud]
       │        │ (DynamoDB Streams: NEW_IMAGE)
       │        ▼
       │    [Lambda: health-adherence-ml-engine]
       │        │ (Dual Inference: RF + XGBoost)
       │        ▼
       │    [DynamoDB: recommendations] (expire_at TTL)
       │
       └──► [Path B: Development Fallback Runner]
                │ (boto3 Polling Daemon: stream_runner.py)
                ▼
            [Production Handler: ml_engine_lambda.process_single_event]
                │ (Dual Inference: RF + XGBoost)
                ▼
            [DynamoDB: recommendations] (expire_at TTL)
```

### 1.2 Root Cause of Cloud Control-Plane Deployment Block
During direct automated deployment using `infra/deploy_ml_engine.ps1`, two external AWS infrastructure prerequisites blocked cloud registration:
1. **IAM Control-Plane Permissions:**  
   The active AWS identity (`arn:aws:iam::751605536502:user/health-adherence-local`) is provisioned with **data-plane permissions** (reading/writing `activity_events`, `recommendations`, and `profiles`), but lacks **control-plane permissions**:
   - `lambda:CreateFunction` (rejected with `AccessDeniedException`)
   - `lambda:PublishLayerVersion` (rejected with `AccessDeniedException`)
   - `lambda:CreateEventSourceMapping` (rejected with `AccessDeniedException`)
   - `dynamodb:UpdateTable` (cannot enable `StreamSpecification` on `activity_events`)
2. **Lambda Layer Direct Upload Ceiling:**  
   The compiled ML dependencies layer (`ml-dependencies-layer.zip`) is **105.55 MB compressed** (243.42 MB uncompressed, which strictly satisfies the AWS 250 MB uncompressed ceiling). However, AWS Lambda API rejects direct CLI uploads larger than 50 MB with connection drop / SSL EOF, requiring the package to be staged in an **Amazon S3 bucket**.

To resolve this completely, two independent paths are provided:
- **Path 1 (Production Cloud Deployment):** Complete remediation instructions and automated script (`infra/setup_cloud_prerequisites.ps1`) for an AWS account administrator.
- **Path 2 (Development Stream Runner Fallback):** Operational local daemon (`backend/runners/stream_runner.py`) that operates using existing data-plane credentials to immediately process live streams with zero code mock facades.

---

## 2. Path 1: Cloud Serverless Deployment (Production Path)

### 2.1 Least-Privilege IAM Policy (`infra/ml_engine_iam_policy.json`)
The exact IAM policy has been authored and committed to `infra/ml_engine_iam_policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaFunctionManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:DeleteFunction",
        "lambda:ListFunctions"
      ],
      "Resource": [
        "arn:aws:lambda:ap-south-1:751605536502:function:health-adherence-ml-engine",
        "arn:aws:lambda:ap-south-1:751605536502:function:iam-perm-probe-ml"
      ]
    },
    {
      "Sid": "LambdaLayerManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:PublishLayerVersion",
        "lambda:GetLayerVersion",
        "lambda:DeleteLayerVersion",
        "lambda:ListLayerVersions"
      ],
      "Resource": [
        "arn:aws:lambda:ap-south-1:751605536502:layer:ml-dependencies-layer",
        "arn:aws:lambda:ap-south-1:751605536502:layer:ml-dependencies-layer:*"
      ]
    },
    {
      "Sid": "LambdaEventSourceMappingManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateEventSourceMapping",
        "lambda:UpdateEventSourceMapping",
        "lambda:GetEventSourceMapping",
        "lambda:DeleteEventSourceMapping",
        "lambda:ListEventSourceMappings"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMPassRoleForLambdaExecution",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::751605536502:role/service-role/health-adherence-processor-role-e3tzuiuz"
    },
    {
      "Sid": "DynamoDBStreamEnablementAndAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateTable",
        "dynamodb:DescribeTable",
        "dynamodb:DescribeStream",
        "dynamodb:GetShardIterator",
        "dynamodb:GetRecords",
        "dynamodb:ListStreams"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-south-1:751605536502:table/activity_events",
        "arn:aws:dynamodb:ap-south-1:751605536502:table/activity_events/stream/*"
      ]
    },
    {
      "Sid": "S3StagingBucketManagement",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:GetBucketLocation",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:PutBucketEncryption",
        "s3:PutBucketPublicAccessBlock"
      ],
      "Resource": [
        "arn:aws:s3:::health-adherence-ml-staging-751605536502",
        "arn:aws:s3:::health-adherence-ml-staging-751605536502/*",
        "arn:aws:s3:::health-adherence-*-staging",
        "arn:aws:s3:::health-adherence-*-staging/*"
      ]
    }
  ]
}
```

### 2.2 Administrator Deployment Procedure
An AWS account administrator can execute the automated deployment in two simple steps:

#### Option A: One-Click PowerShell Script (Recommended)
Run with administrator AWS credentials in PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File infra/setup_cloud_prerequisites.ps1 -AttachPolicy
```
This script automatically:
1. Validates the administrator caller identity.
2. Creates the managed IAM policy `HealthAdherenceMLEnginePolicy` and attaches it to user `health-adherence-local`.
3. Creates the S3 staging bucket `s3://health-adherence-ml-staging-751605536502` with AES256 encryption and public access blocks.
4. Stages `ml-dependencies-layer.zip` to S3 and publishes version 1 of `ml-dependencies-layer`.
5. Creates the `health-adherence-ml-engine` Lambda function (1024 MB RAM, 60s timeout, python3.12).
6. Enables DynamoDB Streams (`NEW_IMAGE`) on `activity_events`.
7. Creates and enables the Event Source Mapping binding the stream to the Lambda function.

#### Option B: AWS CLI Manual Execution
1. Create and attach the policy:
```bash
aws iam create-policy \
    --policy-name HealthAdherenceMLEnginePolicy \
    --policy-document file://infra/ml_engine_iam_policy.json

aws iam attach-user-policy \
    --user-name health-adherence-local \
    --policy-arn arn:aws:iam::751605536502:policy/HealthAdherenceMLEnginePolicy
```
2. Create S3 staging bucket:
```bash
aws s3api create-bucket \
    --bucket health-adherence-ml-staging-751605536502 \
    --region ap-south-1 \
    --create-bucket-configuration LocationConstraint=ap-south-1
```
3. Execute deployment script:
```powershell
powershell -ExecutionPolicy Bypass -File infra/deploy_ml_engine.ps1 -S3Bucket health-adherence-ml-staging-751605536502
```

---

## 3. Path 2: Development Stream Runner Fallback (Operational Path)

### 3.1 Architecture of `backend/runners/stream_runner.py`
To provide immediate development capability without requiring administrator intervention, an operational runner daemon was implemented in `backend/runners/stream_runner.py`.

Key characteristics:
- **Authentic Production Handler:** Calls `backend.functions.ml_engine_lambda.process_single_event` directly, executing the exact identical mathematical feature extraction, dual model inference, TTL calculation, and DynamoDB item writes.
- **Zero Mock Facades:** Connects directly to the live AWS DynamoDB tables in `ap-south-1` using the existing authenticated `health-adherence-local` credentials.
- **Decoupled Asynchronous Processing:** Mirrors DynamoDB Streams by ingesting records with `status: 'received'`, processing them in batches of 1 to 5, writing interventions with 24-hr TTL to `recommendations`, and atomically updating the status to `'processed'`.

### 3.2 Command-Line Usage

#### Single-Pass Execution (Process all pending records and exit)
```bash
python backend/runners/stream_runner.py --once
```
*Use case:* CI/CD pipelines, post-simulation processing, and unit verification.

#### Continuous Polling Daemon (Runs continuously like AWS Lambda)
```bash
python backend/runners/stream_runner.py --interval 2.0 --batch-size 5
```
*Use case:* Local development alongside `iot_simulator/watch_simulator.py`.

#### Reprocess Previously Failed Records
```bash
python backend/runners/stream_runner.py --include-failed --once
```

---

## 4. Adversarial Review & Defect Remediation Record

During independent adversarial review of the runner and Lambda integration, two critical data-plane defects were detected and fixed:

### Defect 1: DynamoDB Scan `Limit` Pre-Filter Starvation
- **Input:** Polling DynamoDB `activity_events` with `Limit=20` and `FilterExpression=status != 'processed'` on a table with 940+ items where the first 100 items were already processed.
- **Expected:** The runner discovers and processes pending records located in later pages.
- **Actual:** The scan evaluated only the first 20 records, filtered all 20 out, and returned 0 items (`Items = []`), falsely reporting that no pending items existed.
- **Root Cause:** In AWS DynamoDB, the `Limit` parameter applies to the number of items evaluated *before* the `FilterExpression` is applied.
- **Fix:** Refactored `fetch_unprocessed_records` to paginate through `LastEvaluatedKey` until `limit` matching items are gathered or the table is exhausted.

### Defect 2: Failed Record Infinite Polling Loop
- **Input:** A legacy malformed record from earlier development lacked sensor data (`event_id=9d39171d...`).
- **Expected:** The corrupted record is marked `'failed'` and skipped on subsequent polling cycles so valid records can progress.
- **Actual:** The runner filter expression was `status != 'processed' AND status != 'archived'`. Because `'failed'` satisfies both conditions, the runner repeatedly fetched the bad record on every iteration, starving other pending events.
- **Root Cause:** Overly broad filter expression that included error states.
- **Fix:** Constrained active intake filter to `(status == 'received' OR status == 'pending' OR attribute_not_exists(status))`, isolating failed records unless explicitly requested via `--include-failed`.

---

## 5. End-to-End Live Verification Record

### 5.1 Automated Unit & Integration Tests
- `scratch/test_ml_lambda.py`: **26/26 tests PASSED** (100% in 2.68s)
- `scratch/test_stream_runner.py`: **4/4 tests PASSED** (100% in 1.14s)

### 5.2 Live End-to-End Telemetry Streaming Verification
1. **Initial State:** DynamoDB `recommendations` table contained 153 items.
2. **Backlog Clearance:** Executed `python backend/runners/stream_runner.py --once`, successfully processing 16 backlog events. Count increased to 169.
3. **IoT Simulation:** Executed `python iot_simulator/watch_simulator.py --max-windows 3`. 3 synchronized 10-second windows were published via MQTT to AWS IoT Core topic `health-adherence/telemetry`.
4. **AWS Ingestion:** AWS IoT Core rule triggered `health-adherence-processor`, writing 3 records to DynamoDB `activity_events` with `status: 'received'`.
5. **Stream Runner Ingestion:** Executed `python backend/runners/stream_runner.py --once`. Output:
   ```
   [STREAM_RUNNER] Discovered 3 unprocessed event(s) in activity_events. Ingesting...
   [STREAM_RUNNER] [SUCCESS] event_id=39291df7-740e-4737-89ea-9c42fb045ab5 -> RecID=rec_1792168188683_65cfb7 | Activity=Eating_Pasta (conf=0.3143) | Risk=0.395 (Medium) | TTL=1792254588
   [STREAM_RUNNER] [SUCCESS] event_id=16295ec5-f352-4c85-9222-8b321c103dcb -> RecID=rec_1792168188922_7e57ae | Activity=Eating_Chips (conf=0.24) | Risk=0.395 (Medium) | TTL=1792254588
   [STREAM_RUNNER] [SUCCESS] event_id=b0e1acab-7943-4ca2-990b-3c9d6676f049 -> RecID=rec_1792168189155_83e7b7 | Activity=Eating_Pasta (conf=0.4317) | Risk=0.395 (Medium) | TTL=1792254589
   ```
6. **Final Verification:** DynamoDB `recommendations` count increased from **169 to 172 items**.
7. **TTL & Item Verification:** Inspection of recommendation item `rec_1792168079927_51b99e` confirmed presence of:
   - `expire_at`: `1792254479` (exactly current Unix epoch + 86,400 seconds)
   - `activity`: `"Kicking_Soccer_Ball"` (confidence: 0.1716)
   - `risk_score`: `0.395` (`risk_band`: `"Medium"`)
   - `health_profile`: 21 clinical BRFSS indicators from authenticated user profile
   - `event_id` & `device_id`: preserved for traceability.
   - Source item in `activity_events` updated to `status: 'processed'`.
