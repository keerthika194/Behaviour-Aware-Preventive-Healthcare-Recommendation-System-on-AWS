import json
import boto3
from decimal import Decimal
import datetime

# ============================================================
# AWS DYNAMODB RESOURCE
# ============================================================

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
profiles_table = dynamodb.Table('profiles')

# ============================================================
# CORS HEADERS (Must be included on EVERY response)
# ============================================================

CORS_HEADERS = {
    'Access-Control-Allow-Origin': 'http://localhost:3000',
    'Access-Control-Allow-Headers': 'Authorization,Content-Type,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Max-Age': '86400',
}

# ============================================================
# HELPER: FLOAT <-> DECIMAL CONVERTERS
# ============================================================

def convert_floats_to_decimals(obj):
    """
    Recursively converts all Python float values to boto3-compatible Decimal objects.
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(i) for i in obj]
    return obj

def convert_decimals_to_native(obj):
    """
    Recursively converts Decimal objects to int or float for standard JSON serialization.
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals_to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals_to_native(i) for i in obj]
    return obj

def decimal_serializer(obj):
    """Fallback JSON serializer for any Decimal instances."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def make_response(status_code, body_dict):
    """
    Constructs a valid API Gateway proxy response with CORS headers and safe JSON encoding.
    """
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(convert_decimals_to_native(body_dict), default=decimal_serializer),
    }

# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):
    """
    Handles GET /profile, POST /profile, and OPTIONS /profile with Cognito JWT Authorization.
    Guarantees CORS headers on every single response, including exceptions and auth failures.
    """
    # Wrap entire execution in top-level try/except to prevent unhandled 502 Bad Gateway
    try:
        # 1. Determine HTTP Method (Compatible with both Payload Format 1.0 and 2.0)
        http_method = (
            event.get('httpMethod')
            or event.get('requestContext', {}).get('http', {}).get('method')
            or ''
        ).upper()

        # 2. Handle CORS Preflight (OPTIONS)
        if http_method == 'OPTIONS':
            return {
                'statusCode': 204,
                'headers': CORS_HEADERS,
                'body': '',
            }

        # 3. Extract authenticated user_id (Cognito sub) from JWT Claims
        # Checks both HTTP API v2 (authorizer.jwt.claims) and REST API (authorizer.claims)
        authorizer = event.get('requestContext', {}).get('authorizer', {})
        jwt_obj = authorizer.get('jwt', {}) if isinstance(authorizer, dict) else {}
        claims = jwt_obj.get('claims') or authorizer.get('claims') or {}

        user_id = claims.get('sub')

        if not user_id:
            print("[AUTH ERROR] Missing or unverified Cognito 'sub' in authorizer claims.")
            return make_response(401, {'error': 'Unauthorized: Missing or invalid Cognito JWT sub claim'})

        print(f"[INFO] Request verified for Cognito user: {user_id} (Method: {http_method})")

        # 4. GET /profile
        if http_method == 'GET':
            response = profiles_table.get_item(Key={'user_id': str(user_id)})
            item = response.get('Item')
            if item:
                item = convert_decimals_to_native(item)
            return make_response(200, item or {'user_id': str(user_id)})

        # 5. POST /profile
        if http_method == 'POST':
            body_raw = event.get('body') or '{}'
            if event.get('isBase64Encoded', False):
                import base64
                body_raw = base64.b64decode(body_raw).decode('utf-8')

            try:
                body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
            except Exception as parse_err:
                print(f"[PARSE ERROR] Invalid JSON body: {parse_err}")
                return make_response(400, {'error': f'Invalid JSON body: {str(parse_err)}'})

            # Always override user_id with the authenticated Cognito sub
            body['user_id'] = str(user_id)
            body['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Convert all floats to Decimals for DynamoDB
            item = convert_floats_to_decimals(body)

            # Persist to DynamoDB profiles table
            profiles_table.put_item(Item=item)

            print(f"[SUCCESS] Profile successfully saved for user: {user_id}")
            return make_response(200, {
                'message': 'Health profile saved successfully.',
                'user_id': str(user_id),
                'profile': body
            })

        # 6. Method Not Allowed
        return make_response(405, {'error': f'Method {http_method} not allowed'})

    except Exception as exc:
        print(f"[FATAL LAMBDA EXCEPTION] {type(exc).__name__}: {str(exc)}")
        # Catch-all exception handler GUARANTEES CORS headers are returned instead of API Gateway 502
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Internal Lambda error: {str(exc)}'}),
        }
