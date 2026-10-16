# ==============================================================================
# AWS ML Engine Cloud Prerequisites Setup & Automated Deployment Script
# ==============================================================================
# Purpose:
# 1. Provisions the S3 staging bucket required for Lambda layers > 50 MB.
# 2. Creates and attaches the least-privilege IAM policy when executed with admin credentials.
# 3. Invokes deploy_ml_engine.ps1 with S3 staging to deploy the Lambda layer,
#    Lambda function, DynamoDB Streams, and Event Source Mapping.
# 4. Performs cloud health verification and diagnostic checks.
# ==============================================================================

[CmdletBinding()]
param(
    [string]$Region = "ap-south-1",
    [string]$S3Bucket = "health-adherence-ml-staging-751605536502",
    [string]$PolicyName = "HealthAdherenceMLEnginePolicy",
    [string]$UserName = "health-adherence-local",
    [string]$RoleArn = "arn:aws:iam::751605536502:role/service-role/health-adherence-processor-role-e3tzuiuz",
    [switch]$AttachPolicy = $false,
    [switch]$SkipDeploy = $false
)

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AWS ML ENGINE CLOUD PREREQUISITES & PROVISIONING" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Region       : $Region"
Write-Host "S3 Bucket    : $S3Bucket"
Write-Host "Target User  : $UserName"
Write-Host "Policy Name  : $PolicyName"
Write-Host "Execution Role: $RoleArn"
Write-Host ""

# Ensure aws CLI is available
$awsCmd = Get-Command "aws" -ErrorAction SilentlyContinue
if (-not $awsCmd) {
    $userScripts = "$env:APPDATA\Python\Python311\Scripts\aws.cmd"
    if (Test-Path $userScripts) {
        $env:PATH += ";$env:APPDATA\Python\Python311\Scripts"
    } else {
        throw "AWS CLI is not found in PATH or Python Scripts folder."
    }
}

# ------------------------------------------------------------------------------
# STEP 1: Verify Active Identity
# ------------------------------------------------------------------------------
Write-Host "[1/4] Verifying AWS Caller Identity..." -ForegroundColor Yellow
$callerJson = aws sts get-caller-identity --output json 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Failed to authenticate with AWS: $callerJson"
}
$callerObj = $callerJson | ConvertFrom-Json
$callerArn = $callerObj.Arn
$accountId = $callerObj.Account
Write-Host "  Active Identity : $callerArn" -ForegroundColor Green
Write-Host "  AWS Account ID  : $accountId" -ForegroundColor Green

# ------------------------------------------------------------------------------
# STEP 2: IAM Policy Provisioning (Optional / Admin execution)
# ------------------------------------------------------------------------------
Write-Host "`n[2/4] Checking IAM Control-Plane Policy..." -ForegroundColor Yellow
$policyFile = Join-Path $PSScriptRoot "ml_engine_iam_policy.json"
if (-not (Test-Path $policyFile)) {
    throw "IAM policy document not found at: $policyFile"
}

$policyArn = "arn:aws:iam::${accountId}:policy/${PolicyName}"
$policyExists = $false

$getPolicyOut = aws iam get-policy --policy-arn $policyArn --output json 2>&1
if ($LASTEXITCODE -eq 0 -and $getPolicyOut -match "Policy") {
    $policyExists = $true
    Write-Host "  IAM Policy already exists: $policyArn" -ForegroundColor Green
} else {
    if ($AttachPolicy) {
        Write-Host "  Creating managed policy '$PolicyName'..."
        $createPolicyOut = aws iam create-policy `
            --policy-name $PolicyName `
            --policy-document "file://$policyFile" `
            --description "Least-privilege policy for Health Adherence ML Engine serverless deployment" `
            --output json 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Created IAM Policy: $policyArn" -ForegroundColor Green
            $policyExists = $true
        } else {
            Write-Warning "Could not create IAM policy: $createPolicyOut"
        }
    } else {
        Write-Host "  IAM Policy '$PolicyName' not yet provisioned. (Pass -AttachPolicy to create/attach automatically if run by an admin)." -ForegroundColor Yellow
    }
}

if ($policyExists -and $AttachPolicy) {
    Write-Host "  Attaching policy $PolicyName to user $UserName..."
    $attachOut = aws iam attach-user-policy --user-name $UserName --policy-arn $policyArn 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Attached policy to user $UserName." -ForegroundColor Green
    } else {
        Write-Warning "Could not attach policy to user $UserName: $attachOut"
    }
}

# ------------------------------------------------------------------------------
# STEP 3: Provision S3 Staging Bucket
# ------------------------------------------------------------------------------
Write-Host "`n[3/4] Ensuring S3 Staging Bucket exists ($S3Bucket)..." -ForegroundColor Yellow

$bucketExists = $false
$headOut = aws s3api head-bucket --bucket $S3Bucket --region $Region 2>&1
if ($LASTEXITCODE -eq 0) {
    $bucketExists = $true
    Write-Host "  [OK] S3 Staging Bucket '$S3Bucket' is accessible." -ForegroundColor Green
} else {
    Write-Host "  Creating S3 Bucket 's3://$S3Bucket' in region '$Region'..."
    if ($Region -eq "us-east-1") {
        $createBucketOut = aws s3api create-bucket --bucket $S3Bucket --region $Region 2>&1
    } else {
        $createBucketOut = aws s3api create-bucket `
            --bucket $S3Bucket `
            --region $Region `
            --create-bucket-configuration "LocationConstraint=$Region" 2>&1
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] S3 Bucket 's3://$S3Bucket' created successfully." -ForegroundColor Green
        $bucketExists = $true

        # Enable SSE-S3 (AES256) default encryption
        Write-Host "  Enabling AES256 server-side encryption on s3://$S3Bucket..."
        $encConfig = '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'
        aws s3api put-bucket-encryption `
            --bucket $S3Bucket `
            --server-side-encryption-configuration $encConfig `
            --region $Region 2>$null | Out-Null

        # Block public access
        Write-Host "  Enabling S3 Block Public Access on s3://$S3Bucket..."
        aws s3api put-public-access-block `
            --bucket $S3Bucket `
            --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" `
            --region $Region 2>$null | Out-Null
    } else {
        Write-Warning "Could not create S3 bucket '$S3Bucket': $createBucketOut"
        if ($createBucketOut -match "AccessDenied") {
            Write-Warning "The active AWS credentials lack 's3:CreateBucket' permissions. Bucket must be created by administrator or provided via -S3Bucket."
        }
    }
}

# ------------------------------------------------------------------------------
# STEP 4: Automated Deployment via deploy_ml_engine.ps1
# ------------------------------------------------------------------------------
if (-not $SkipDeploy) {
    Write-Host "`n[4/4] Executing Serverless Deployment Script..." -ForegroundColor Yellow
    $deployScript = Join-Path $PSScriptRoot "deploy_ml_engine.ps1"
    if (-not (Test-Path $deployScript)) {
        throw "deploy_ml_engine.ps1 script not found at: $deployScript"
    }

    $deployArgs = @{
        Region = $Region
        S3Bucket = $S3Bucket
        RoleArn = $RoleArn
    }

    & $deployScript @deployArgs
} else {
    Write-Host "`n[4/4] Deployment skipped (-SkipDeploy specified)." -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  SETUP & PREREQUISITES EXECUTION COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
