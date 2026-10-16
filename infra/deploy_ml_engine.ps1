# ==============================================================================
# AWS Lambda ML Engine Deployment Script
# ==============================================================================
# Function: health-adherence-ml-engine
# Region: ap-south-1
# Runtime: python3.12
# Pattern: Decoupled DynamoDB Streams (Pattern B)
# ==============================================================================

[CmdletBinding()]
param(
    [string]$Region = "ap-south-1",
    [string]$FunctionName = "health-adherence-ml-engine",
    [string]$LayerName = "ml-dependencies-layer",
    [string]$TableName = "activity_events",
    [int]$BatchSize = 5,
    [int]$MemorySize = 1024,
    [int]$Timeout = 60,
    [string]$RoleArn = "arn:aws:iam::751605536502:role/service-role/health-adherence-processor-role-e3tzuiuz",
    [string]$S3Bucket = "",
    [string]$LayerArn = "",
    [switch]$SkipLayerPublish = $false
)

$ErrorActionPreference = "Continue"
$IamErrors = @()

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $PSScriptRoot "dist"
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AWS ML INFERENCE ENGINE DEPLOYMENT (Pattern B)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Project Root : $ProjectRoot"
Write-Host "Region       : $Region"
Write-Host "Function Name: $FunctionName"
Write-Host "Layer Name   : $LayerName"
Write-Host "Target Table : $TableName"
Write-Host "Batch Size   : $BatchSize"
Write-Host ""

# Ensure aws CLI is available
$awsCmd = Get-Command "aws" -ErrorAction SilentlyContinue
if (-not $awsCmd) {
    # Check User AppData Python Scripts
    $userScripts = "$env:APPDATA\Python\Python311\Scripts\aws.cmd"
    if (Test-Path $userScripts) {
        $env:PATH += ";$env:APPDATA\Python\Python311\Scripts"
    } else {
        throw "AWS CLI is not found in PATH or Python Scripts folder."
    }
}

# ------------------------------------------------------------------------------
# STEP 1: Package Lambda Layer (ml-dependencies-layer)
# ------------------------------------------------------------------------------
Write-Host "[1/4] Packaging Lambda Layer ($LayerName)..." -ForegroundColor Yellow

$LayerSourceDir = Join-Path $ProjectRoot "backend\lambda_layer"
$LayerZipPath = Join-Path $DistDir "ml-dependencies-layer.zip"

if (-not (Test-Path (Join-Path $LayerSourceDir "python"))) {
    throw "Lambda layer python directory not found at $LayerSourceDir\python"
}

# Use python zipfile for reproducible, cross-platform packaging
$layerPackagerScript = @"
import os
import zipfile

source_dir = r'$LayerSourceDir'
zip_path = r'$LayerZipPath'

print(f'Compressing {source_dir} into {zip_path} (optimizing for AWS 250MB uncompressed limit)...')
excluded_dirs = {'nvidia', 'tests', 'test', '__pycache__', 'pandas', 'narwhals', 'bin'}
excluded_exts = {'.pyc', '.pyo', '.gitkeep', '.pyi', '.h', '.c', '.pxd', '.md', '.txt'}

with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for root, dirs, files in os.walk(os.path.join(source_dir, 'python')):
        parts = root.split(os.sep)
        # Exclude directories
        if any(p in excluded_dirs or p.endswith('.dist-info') or p.endswith('.egg-info') for p in parts):
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in excluded_exts or file.startswith('.'):
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, source_dir)
            zf.write(full_path, rel_path)

total_uncompressed = sum(i.file_size for i in zf.infolist())
total_mb = total_uncompressed / (1024 * 1024)
print(f'Layer packaging complete. Uncompressed size: {total_mb:.2f} MB (AWS Limit: 250 MB).')
if total_mb > 250.0:
    raise RuntimeError(f'Layer uncompressed size {total_mb:.2f} MB exceeds AWS Lambda 250 MB limit!')
"@

$layerZipNeedsRebuild = $true
if (Test-Path $LayerZipPath) {
    # Check if existing layer zip is strictly compliant with 250MB uncompressed limit
    $uncompressedCheck = python -c "import zipfile, os; z = zipfile.ZipFile(r'$LayerZipPath'); sz = sum(i.file_size for i in z.infolist()) / (1024*1024); print(f'{sz:.2f}'); z.close()" 2>$null
    if ($uncompressedCheck -and [double]$uncompressedCheck -lt 250.0) {
        Write-Host "  Existing layer zip is compliant ($uncompressedCheck MB uncompressed < 250 MB limit): $LayerZipPath"
        $layerZipNeedsRebuild = $false
    }
}

if ($layerZipNeedsRebuild) {
    Write-Host "  Building compliant layer package $LayerZipPath..."
    python -c $layerPackagerScript
}

$layerZipSizeMB = [math]::Round(((Get-Item $LayerZipPath).Length / 1MB), 2)
$uncompressedMB = python -c "import zipfile; z = zipfile.ZipFile(r'$LayerZipPath'); print(f'{sum(i.file_size for i in z.infolist()) / (1024*1024):.2f}'); z.close()"
Write-Host "  [OK] Layer package: $layerZipSizeMB MB compressed | $uncompressedMB MB uncompressed (Limit: 250 MB)" -ForegroundColor Green

# Publish Layer Version
if ($LayerArn) {
    Write-Host "  Using specified Layer ARN: $LayerArn" -ForegroundColor Green
} elseif ($SkipLayerPublish) {
    Write-Host "  Skipping layer publishing (-SkipLayerPublish specified)." -ForegroundColor Yellow
    $LayerArn = $null
} else {
    Write-Host "  Publishing Lambda Layer to AWS ($Region)..."
    if ($S3Bucket) {
        Write-Host "  Uploading layer zip to s3://$S3Bucket/$LayerName.zip..."
        aws s3 cp $LayerZipPath "s3://$S3Bucket/$LayerName.zip" --region $Region
        $publishLayerOutput = aws lambda publish-layer-version `
            --layer-name $LayerName `
            --description "Scikit-Learn, XGBoost, NumPy dependencies for health ML engine" `
            --content "S3Bucket=$S3Bucket,S3Key=$LayerName.zip" `
            --compatible-runtimes python3.11 python3.12 `
            --region $Region `
            --output json 2>&1
    } else {
        if ((Get-Item $LayerZipPath).Length -gt 50MB) {
            Write-Warning "Layer package ($layerZipSizeMB MB) exceeds the 50 MB direct zip upload limit of the AWS Lambda API."
            Write-Warning "AWS rejects direct CLI payloads > 50 MB with connection drop / SSL EOF."
            Write-Warning "To publish this layer, stage the package via Amazon S3: pass -S3Bucket <bucket-name>, or supply an existing -LayerArn <arn>."
            Write-Host "  Skipping direct API upload of $layerZipSizeMB MB layer to prevent connection hang." -ForegroundColor Yellow
            $publishLayerOutput = "Direct upload skipped: package exceeds 50MB and -S3Bucket was not provided."
            $LayerArn = $null
        } else {
            $publishLayerOutput = aws lambda publish-layer-version `
                --layer-name $LayerName `
                --description "Scikit-Learn, XGBoost, NumPy dependencies for health ML engine" `
                --zip-file "fileb://$LayerZipPath" `
                --compatible-runtimes python3.11 python3.12 `
                --region $Region `
                --output json 2>&1
        }
    }

    if ($LayerArn) {
        # Already provided via parameter
    } elseif ($LASTEXITCODE -eq 0 -and $publishLayerOutput -match "LayerVersionArn") {
        $layerJson = $publishLayerOutput | ConvertFrom-Json
        $LayerArn = $layerJson.LayerVersionArn
        Write-Host "  [OK] Published Layer ARN: $LayerArn" -ForegroundColor Green
    } else {
        if ($publishLayerOutput -notmatch "Direct upload skipped") {
            Write-Warning "Could not publish layer via AWS CLI: $publishLayerOutput"
            if ($publishLayerOutput -match "AccessDeniedException") {
                $IamErrors += "lambda:PublishLayerVersion"
            }
        }
        $LayerArn = $null
    }
}

# ------------------------------------------------------------------------------
# STEP 2: Package Function Code and Model Artifacts
# ------------------------------------------------------------------------------
Write-Host "`n[2/4] Packaging Lambda Function ($FunctionName)..." -ForegroundColor Yellow

$FunctionZipPath = Join-Path $DistDir "ml_engine_function.zip"
$HandlerFile = Join-Path $ProjectRoot "backend\functions\ml_engine_lambda.py"
$ModelsDir = Join-Path $ProjectRoot "models"

if (-not (Test-Path $HandlerFile)) {
    throw "Handler file not found: $HandlerFile"
}

$functionPackagerScript = @"
import os
import zipfile

zip_path = r'$FunctionZipPath'
handler_file = r'$HandlerFile'
models_dir = r'$ModelsDir'

print(f'Creating function deployment package at {zip_path}...')
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    # Handler file at root
    zf.write(handler_file, 'ml_engine_lambda.py')
    
    # Model artifacts under models/
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.endswith('.pyc') or file == '.gitkeep' or file.endswith('.csv'):
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, os.path.dirname(models_dir))
            zf.write(full_path, rel_path)
print('Function packaging complete.')
"@

python -c $functionPackagerScript
$funcZipSizeMB = [math]::Round(((Get-Item $FunctionZipPath).Length / 1MB), 2)
Write-Host "  [OK] Function package size: $funcZipSizeMB MB" -ForegroundColor Green

# ------------------------------------------------------------------------------
# STEP 3: Deploy or Update Lambda Function
# ------------------------------------------------------------------------------
Write-Host "`n[3/4] Deploying Lambda Function ($FunctionName)..." -ForegroundColor Yellow

$functionExists = $false
try {
    $listFuncs = aws lambda list-functions --region $Region --output json 2>$null | ConvertFrom-Json
    $matched = $listFuncs.Functions | Where-Object { $_.FunctionName -eq $FunctionName }
    if ($matched) {
        $functionExists = $true
    }
} catch {
    $functionExists = $false
}

if ($functionExists) {
    Write-Host "  Function '$FunctionName' already exists. Updating code and configuration..."
    if ($S3Bucket) {
        Write-Host "  Uploading function zip to s3://$S3Bucket/ml_engine_function.zip..."
        aws s3 cp $FunctionZipPath "s3://$S3Bucket/ml_engine_function.zip" --region $Region
        aws lambda update-function-code `
            --function-name $FunctionName `
            --s3-bucket $S3Bucket `
            --s3-key "ml_engine_function.zip" `
            --region $Region | Out-Null
    } else {
        aws lambda update-function-code `
            --function-name $FunctionName `
            --zip-file "fileb://$FunctionZipPath" `
            --region $Region | Out-Null
    }

    Start-Sleep -Seconds 3

    if ($LayerArn) {
        aws lambda update-function-configuration `
            --function-name $FunctionName `
            --layers $LayerArn `
            --memory-size $MemorySize `
            --timeout $Timeout `
            --region $Region | Out-Null
    } else {
        aws lambda update-function-configuration `
            --function-name $FunctionName `
            --memory-size $MemorySize `
            --timeout $Timeout `
            --region $Region | Out-Null
    }
    Write-Host "  [OK] Lambda function updated successfully." -ForegroundColor Green
} else {
    Write-Host "  Creating new Lambda function '$FunctionName'..."

    # Pre-flight check lambda:CreateFunction permissions with a tiny probe to avoid multi-minute upload hangs
    Write-Host "  Verifying 'lambda:CreateFunction' IAM permission before uploading $funcZipSizeMB MB..."
    $probeZip = Join-Path $DistDir "probe.zip"
    python -c "import zipfile; z = zipfile.ZipFile(r'$probeZip', 'w'); z.writestr('lambda_function.py', 'def lambda_handler(e, c): pass'); z.close()"
    $probeOutput = aws lambda create-function `
        --function-name "iam-perm-probe-ml" `
        --runtime "python3.12" `
        --role $RoleArn `
        --handler "lambda_function.lambda_handler" `
        --zip-file "fileb://$probeZip" `
        --region $Region 2>&1
    Remove-Item $probeZip -Force -ErrorAction SilentlyContinue

    if ($probeOutput -match "AccessDeniedException") {
        Write-Warning "Could not create Lambda function: $probeOutput"
        $createOutput = $probeOutput
        $IamErrors += "lambda:CreateFunction"
    } else {
        if ($probeOutput -match "FunctionArn") {
            # Clean up probe function if it succeeded
            aws lambda delete-function --function-name "iam-perm-probe-ml" --region $Region 2>$null | Out-Null
        }

        if ($S3Bucket) {
            Write-Host "  Uploading function zip to s3://$S3Bucket/ml_engine_function.zip..."
            aws s3 cp $FunctionZipPath "s3://$S3Bucket/ml_engine_function.zip" --region $Region
            $createParams = @(
                "lambda", "create-function",
                "--function-name", $FunctionName,
                "--runtime", "python3.12",
                "--role", $RoleArn,
                "--handler", "ml_engine_lambda.lambda_handler",
                "--memory-size", "$MemorySize",
                "--timeout", "$Timeout",
                "--code", "S3Bucket=$S3Bucket,S3Key=ml_engine_function.zip",
                "--region", $Region
            )
        } else {
            $createParams = @(
                "lambda", "create-function",
                "--function-name", $FunctionName,
                "--runtime", "python3.12",
                "--role", $RoleArn,
                "--handler", "ml_engine_lambda.lambda_handler",
                "--memory-size", "$MemorySize",
                "--timeout", "$Timeout",
                "--zip-file", "fileb://$FunctionZipPath",
                "--region", $Region
            )
        }
        if ($LayerArn) {
            $createParams += @("--layers", $LayerArn)
        }

        $createOutput = & aws @createParams 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Lambda function created successfully." -ForegroundColor Green
            $functionExists = $true
        } else {
            Write-Warning "Could not create Lambda function: $createOutput"
            if ($createOutput -match "AccessDeniedException") {
                $IamErrors += "lambda:CreateFunction"
            }
        }
    }
}

# ------------------------------------------------------------------------------
# STEP 4: DynamoDB Streams & Event Source Mapping
# ------------------------------------------------------------------------------
Write-Host "`n[4/4] Configuring DynamoDB Streams & Event Source Mapping..." -ForegroundColor Yellow

# Check DynamoDB table stream status
$tableDesc = aws dynamodb describe-table --table-name $TableName --region $Region --output json 2>$null | ConvertFrom-Json
$streamSpec = $tableDesc.Table.StreamSpecification

if (-not $streamSpec -or -not $streamSpec.StreamEnabled) {
    Write-Host "  Enabling DynamoDB Streams on '$TableName' with NEW_IMAGE view type..."
    $updateOutput = aws dynamodb update-table `
        --table-name $TableName `
        --stream-specification "StreamEnabled=true,StreamViewType=NEW_IMAGE" `
        --region $Region 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] DynamoDB Streams requested." -ForegroundColor Green
        
        # Poll until stream is ready
        $maxRetries = 10
        do {
            Start-Sleep -Seconds 2
            $tableDesc = aws dynamodb describe-table --table-name $TableName --region $Region --output json | ConvertFrom-Json
            $maxRetries--
        } while ((-not $tableDesc.Table.LatestStreamArn) -and ($maxRetries -gt 0))
    } else {
        Write-Warning "Notice updating table stream: $updateOutput"
        if ($updateOutput -match "AccessDeniedException") {
            $IamErrors += "dynamodb:UpdateTable"
        }
    }
}

$streamArn = $tableDesc.Table.LatestStreamArn
if ($streamArn) {
    Write-Host "  DynamoDB Stream ARN: $streamArn" -ForegroundColor Cyan
    
    # Check existing Event Source Mappings
    $mappings = aws lambda list-event-source-mappings `
        --function-name $FunctionName `
        --event-source-arn $streamArn `
        --region $Region --output json 2>$null | ConvertFrom-Json

    $existingMapping = $mappings.EventSourceMappings | Where-Object { $_.FunctionArn -match $FunctionName }

    if ($existingMapping) {
        Write-Host "  Existing Event Source Mapping found ($($existingMapping.UUID)). Ensuring enabled with batch size $BatchSize..."
        aws lambda update-event-source-mapping `
            --uuid $existingMapping.UUID `
            --batch-size $BatchSize `
            --enabled `
            --region $Region | Out-Null
        Write-Host "  [OK] Event Source Mapping updated (UUID: $($existingMapping.UUID))." -ForegroundColor Green
    } else {
        Write-Host "  Creating Event Source Mapping for '$FunctionName'..."
        try {
            $esm = aws lambda create-event-source-mapping `
                --function-name $FunctionName `
                --event-source-arn $streamArn `
                --starting-position LATEST `
                --batch-size $BatchSize `
                --enabled `
                --region $Region --output json 2>&1 | ConvertFrom-Json
            Write-Host "  [OK] Event Source Mapping created (UUID: $($esm.UUID), State: $($esm.State))." -ForegroundColor Green
        } catch {
            Write-Warning "Could not create event source mapping: $_"
            if ($_ -match "AccessDeniedException") {
                $IamErrors += "lambda:CreateEventSourceMapping"
            }
        }
    }
} else {
    Write-Host "  [NOTICE] LatestStreamArn is not currently available for table '$TableName'." -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT STATUS & DIAGNOSTIC SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Artifact Status:"
Write-Host "  - Dependencies Layer Package : $LayerZipPath ($layerZipSizeMB MB compressed | $uncompressedMB MB uncompressed)"
Write-Host "  - Lambda Function Package    : $FunctionZipPath ($funcZipSizeMB MB)"

Write-Host "`nCloud Infrastructure Status ($Region):"
if ($LayerArn) {
    Write-Host "  - Lambda Layer Version       : DEPLOYED ($LayerArn)" -ForegroundColor Green
} else {
    Write-Host "  - Lambda Layer Version       : NOT DEPLOYED (Requires -S3Bucket staging for packages >50MB and lambda:PublishLayerVersion)" -ForegroundColor Yellow
}
if ($functionExists) {
    Write-Host "  - Lambda ML Engine           : DEPLOYED ($FunctionName)" -ForegroundColor Green
} else {
    Write-Host "  - Lambda ML Engine           : NOT DEPLOYED (Pending lambda:CreateFunction permission)" -ForegroundColor Yellow
}
if ($streamArn) {
    Write-Host "  - DynamoDB Streams           : ACTIVE ($streamArn)" -ForegroundColor Green
} else {
    Write-Host "  - DynamoDB Streams           : NOT ENABLED (Pending dynamodb:UpdateTable permission)" -ForegroundColor Yellow
}

if ($IamErrors.Count -gt 0) {
    Write-Host "`n[IAM CONTROL-PLANE PERMISSION PREREQUISITES]" -ForegroundColor Yellow
    Write-Host "The active AWS IAM identity lacks administrative permissions to provision cloud infrastructure."
    Write-Host "Missing control-plane actions identified:"
    foreach ($err in ($IamErrors | Select-Object -Unique)) {
        Write-Host "  * $err" -ForegroundColor Red
    }
    Write-Host "`nTo complete cloud provisioning, an AWS account administrator must attach an IAM policy"
    Write-Host "granting the above actions, and provide an S3 bucket (-S3Bucket <name>) to stage the layer."
} else {
    Write-Host "`nAll operations completed successfully." -ForegroundColor Green
}
Write-Host "============================================================" -ForegroundColor Cyan
