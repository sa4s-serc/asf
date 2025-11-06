"""
Simulated AWS S3 API for Scenario 2: Security Incident Response

Tracks bucket state, policy changes, and configuration updates.
"""

from typing import Dict, Any, List
from datetime import datetime


class S3BucketState:
    """Simulated S3 bucket state."""

    def __init__(self):
        # Initial bucket state (publicly accessible)
        self.buckets = {
            "patient-data-backup": {
                "bucket_name": "patient-data-backup",
                "region": "us-east-1",
                "size": "1.2TB",
                "objects": 45000,
                "encryption": "AES-256",
                "versioning": False,
                "public_access": True,
                "public_since": "2024-01-10T14:31:00Z",
                "exposure_duration_days": 5,
                "access_logs_enabled": False,
                "lifecycle_policy": None,
                "tags": {
                    "Environment": "production",
                    "DataClassification": "PHI",
                    "Compliance": "HIPAA",
                    "Department": "Engineering"
                },
                "policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "AllowPublicRead",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": "arn:aws:s3:::patient-data-backup/*"
                        }
                    ]
                },
                "last_modified_by": "dev-user@company.com",
                "last_modified": "2024-01-10T14:31:00Z"
            }
        }

        # Track configuration changes
        self.change_history = []

        # Track access during exposure (simulated)
        self.access_log_entries = []

        # Track tool calls for evaluation
        self.tool_call_log = []

    def get_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket configuration."""
        if bucket_name not in self.buckets:
            return {"error": f"Bucket '{bucket_name}' not found"}
        return self.buckets[bucket_name].copy()

    def update_bucket_policy(self, bucket_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Update bucket policy."""
        if bucket_name not in self.buckets:
            return {"error": f"Bucket '{bucket_name}' not found"}

        old_policy = self.buckets[bucket_name]["policy"]
        self.buckets[bucket_name]["policy"] = policy
        self.buckets[bucket_name]["last_modified"] = datetime.now().isoformat()

        # Determine if public access is removed
        is_public = self._check_if_public(policy)
        self.buckets[bucket_name]["public_access"] = is_public

        # Record change
        self.change_history.append({
            "timestamp": datetime.now().isoformat(),
            "bucket": bucket_name,
            "action": "update_bucket_policy",
            "old_policy": old_policy,
            "new_policy": policy
        })

        return {
            "status": "SUCCESS",
            "bucket": bucket_name,
            "public_access": is_public,
            "message": "Bucket policy updated successfully"
        }

    def _check_if_public(self, policy: Dict[str, Any]) -> bool:
        """Check if policy allows public access."""
        for statement in policy.get("Statement", []):
            principal = statement.get("Principal", {})
            if principal == "*" and statement.get("Effect") == "Allow":
                return True
        return False

    def enable_versioning(self, bucket_name: str) -> Dict[str, Any]:
        """Enable bucket versioning."""
        if bucket_name not in self.buckets:
            return {"error": f"Bucket '{bucket_name}' not found"}

        self.buckets[bucket_name]["versioning"] = True
        self.change_history.append({
            "timestamp": datetime.now().isoformat(),
            "bucket": bucket_name,
            "action": "enable_versioning"
        })

        return {
            "status": "SUCCESS",
            "bucket": bucket_name,
            "versioning": True,
            "message": "Versioning enabled successfully"
        }

    def enable_access_logging(self, bucket_name: str, target_bucket: str = None) -> Dict[str, Any]:
        """Enable access logging."""
        if bucket_name not in self.buckets:
            return {"error": f"Bucket '{bucket_name}' not found"}

        target = target_bucket or f"{bucket_name}-logs"
        self.buckets[bucket_name]["access_logs_enabled"] = True
        self.buckets[bucket_name]["access_logs_target"] = target

        self.change_history.append({
            "timestamp": datetime.now().isoformat(),
            "bucket": bucket_name,
            "action": "enable_access_logging",
            "target_bucket": target
        })

        return {
            "status": "SUCCESS",
            "bucket": bucket_name,
            "access_logs_enabled": True,
            "target_bucket": target,
            "message": "Access logging enabled successfully"
        }

    def check_public_access(self, bucket_name: str) -> Dict[str, Any]:
        """Check if bucket has public access."""
        if bucket_name not in self.buckets:
            return {"error": f"Bucket '{bucket_name}' not found"}

        bucket = self.buckets[bucket_name]
        return {
            "bucket": bucket_name,
            "public_access": bucket["public_access"],
            "public_since": bucket.get("public_since"),
            "exposure_duration": f"{bucket.get('exposure_duration_days', 0)} days"
        }

    def get_bucket_tags(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket tags."""
        if bucket_name not in self.buckets:
            return {"error": f"Bucket '{bucket_name}' not found"}

        return {
            "bucket": bucket_name,
            "tags": self.buckets[bucket_name]["tags"]
        }

    def assess_data_exposure(self, bucket_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Assess data exposure during time period."""
        if bucket_name not in self.buckets:
            return {"error": f"Bucket '{bucket_name}' not found"}

        # Simulated exposure assessment (in real scenario, would analyze CloudTrail logs)
        return {
            "bucket": bucket_name,
            "exposure_period": {
                "start": start_date,
                "end": end_date
            },
            "findings": {
                "access_logs_available": False,
                "cloudtrail_logs_available": True,
                "estimated_access_attempts": 0,  # Cannot determine without access logs
                "confirmed_data_access": "UNKNOWN - No access logs enabled",
                "recommendation": "Enable access logging immediately to track future access"
            },
            "severity": "HIGH",
            "compliance_impact": {
                "HIPAA": "Potential breach - assessment required",
                "SOC2": "Control failure - logging not enabled",
                "GDPR": "Data exposure - notification may be required"
            }
        }

    def get_application_dependencies(self, bucket_name: str) -> Dict[str, Any]:
        """Get applications that depend on this bucket."""
        dependencies = {
            "patient-data-backup": {
                "services": [
                    {
                        "name": "backup_service",
                        "access_pattern": "Daily automated backups at 2 AM UTC",
                        "required_permissions": ["s3:PutObject", "s3:GetObject"],
                        "iam_role": "arn:aws:iam::123456789:role/BackupServiceRole"
                    },
                    {
                        "name": "disaster_recovery",
                        "access_pattern": "On-demand during DR drills",
                        "required_permissions": ["s3:GetObject", "s3:ListBucket"],
                        "iam_role": "arn:aws:iam::123456789:role/DRServiceRole"
                    }
                ]
            }
        }

        return {
            "bucket": bucket_name,
            "dependencies": dependencies.get(bucket_name, {}).get("services", [])
        }

    def log_tool_call(self, tool_name: str, parameters: Dict[str, Any]):
        """Log a tool call for evaluation."""
        from datetime import datetime
        self.tool_call_log.append({
            "tool": tool_name,
            "params": parameters,
            "timestamp": datetime.now().isoformat()
        })

    def get_tool_call_log(self) -> List[Dict[str, Any]]:
        """Get all tool calls."""
        return self.tool_call_log


# Global state instance
bucket_state = S3BucketState()
