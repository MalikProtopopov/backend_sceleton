#!/usr/bin/env python3
"""Script to diagnose media serving issues.

Usage:
    python scripts/check_media.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from botocore.config import Config

# Load environment variables
from dotenv import load_dotenv

env_file = backend_dir / ".env.prod"
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"⚠️  Warning: {env_file} not found, using system environment variables")

# Get settings
s3_endpoint = os.getenv("S3_ENDPOINT_URL", "")
s3_access_key = os.getenv("S3_ACCESS_KEY", "")
s3_secret_key = os.getenv("S3_SECRET_KEY", "")
s3_bucket = os.getenv("S3_BUCKET_NAME", "cms-assets")
s3_region = os.getenv("S3_REGION", "us-east-1")

print("=" * 60)
print("Media/S3 Configuration Check")
print("=" * 60)
print()

# Check configuration
print("📋 Configuration:")
print(f"  S3_ENDPOINT_URL: {s3_endpoint or '(not set)'}")
print(f"  S3_ACCESS_KEY: {'*' * len(s3_access_key) if s3_access_key else '(not set)'}")
print(f"  S3_SECRET_KEY: {'*' * len(s3_secret_key) if s3_secret_key else '(not set)'}")
print(f"  S3_BUCKET_NAME: {s3_bucket}")
print(f"  S3_REGION: {s3_region}")
print()

if not s3_access_key or not s3_secret_key:
    print("❌ ERROR: S3 credentials not configured!")
    print("   Set S3_ACCESS_KEY and S3_SECRET_KEY in .env.prod")
    sys.exit(1)

if not s3_endpoint:
    print("⚠️  WARNING: S3_ENDPOINT_URL not set")
    print("   Using default AWS S3 endpoint")
    print()

# Try to connect
print("🔌 Testing S3 connection...")
try:
    client = boto3.client(
        "s3",
        endpoint_url=s3_endpoint or None,
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_key,
        region_name=s3_region,
        config=Config(signature_version="s3v4"),
    )
    
    # Test connection by listing buckets
    print("  → Listing buckets...")
    buckets = client.list_buckets()
    print(f"  ✅ Connected! Found {len(buckets.get('Buckets', []))} bucket(s)")
    
    # Check if target bucket exists
    bucket_names = [b["Name"] for b in buckets.get("Buckets", [])]
    if s3_bucket in bucket_names:
        print(f"  ✅ Bucket '{s3_bucket}' exists")
        
        # Try to list objects
        print(f"  → Listing objects in '{s3_bucket}'...")
        try:
            objects = client.list_objects_v2(Bucket=s3_bucket, MaxKeys=5)
            count = objects.get("KeyCount", 0)
            if count > 0:
                print(f"  ✅ Found {count} object(s) (showing first 5)")
                for obj in objects.get("Contents", [])[:5]:
                    print(f"     - {obj['Key']} ({obj['Size']} bytes)")
            else:
                print(f"  ⚠️  Bucket is empty")
        except ClientError as e:
            print(f"  ❌ Error listing objects: {e}")
    else:
        print(f"  ❌ Bucket '{s3_bucket}' NOT FOUND!")
        print(f"     Available buckets: {', '.join(bucket_names) if bucket_names else 'none'}")
        print(f"     Create bucket or update S3_BUCKET_NAME in .env.prod")
    
except EndpointConnectionError as e:
    print(f"  ❌ Cannot connect to S3 endpoint: {e}")
    print()
    print("  Troubleshooting:")
    if "minio" in s3_endpoint.lower():
        print("  - Is MinIO container running? Check: docker ps | grep minio")
        print("  - Is S3_ENDPOINT_URL correct? Should be 'http://minio:9000' for Docker network")
        print("  - Are containers in the same Docker network?")
    else:
        print("  - Check if S3_ENDPOINT_URL is correct and accessible")
        print("  - Check network connectivity and firewall rules")
    sys.exit(1)
    
except ClientError as e:
    error_code = e.response.get("Error", {}).get("Code", "Unknown")
    print(f"  ❌ S3 API Error: {error_code}")
    print(f"     {e}")
    print()
    print("  Troubleshooting:")
    if error_code == "InvalidAccessKeyId":
        print("  - Check S3_ACCESS_KEY in .env.prod")
    elif error_code == "SignatureDoesNotMatch":
        print("  - Check S3_SECRET_KEY in .env.prod")
    elif error_code == "NoSuchBucket":
        print(f"  - Bucket '{s3_bucket}' does not exist")
        print("  - Create bucket or update S3_BUCKET_NAME")
    sys.exit(1)
    
except Exception as e:
    print(f"  ❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("✅ S3 connection test completed")
print("=" * 60)
print()
print("Next steps:")
print("  1. Test media endpoint: curl http://localhost:8000/media/{tenant_id}/cases/test.png")
print("  2. Check backend logs: docker logs cms_backend_prod | grep media_serve_error")
print("  3. Verify MinIO is running: docker ps | grep minio")
