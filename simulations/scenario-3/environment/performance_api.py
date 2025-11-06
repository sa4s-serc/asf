"""
Performance API for Scenario 3: Performance Degradation RCA

Simulates AWS environment state with performance metrics, security groups,
network configuration, and change history tracking.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class PerformanceAPI:
    """Simulated AWS environment for performance degradation scenario."""

    def __init__(self):
        """Initialize environment with the problematic state."""

        # Timeline: Issue started at 08:20, we're investigating at 10:05
        self.current_time = datetime(2024, 1, 15, 10, 5, 0)

        # Service state (showing degraded performance)
        self.services = {
            "payment-service": {
                "name": "payment-service",
                "status": "degraded",
                "instances": ["i-abc123", "i-abc124", "i-abc125"],
                "instance_type": "m5.xlarge",
                "instance_count": 3,
                "region": "us-east-1",
                "load_balancer": "alb-payment-prod",
                "database": "prod-payment-db",
                "subnet": "10.0.2.0/24",
                "security_group": "sg-app-tier"
            }
        }

        # Performance metrics (current degraded state)
        self.metrics = {
            "payment-service": {
                "avg_response_time": 2.4,  # seconds
                "p95_response_time": 3.8,
                "p99_response_time": 5.2,
                "error_rate": 5.2,  # percent
                "cpu_utilization": 85,  # percent
                "memory_utilization": 72,  # percent
                "network_in": 120,  # MB/s
                "network_out": 85,  # MB/s
                "throughput": 650,  # requests/min
                "active_connections": 450,
                "failed_connections": 180  # This is the smoking gun
            }
        }

        # Database state
        self.databases = {
            "prod-payment-db": {
                "endpoint": "prod-payment-db.cluster-xyz.us-east-1.rds.amazonaws.com",
                "port": 5432,
                "engine": "PostgreSQL",
                "subnet": "10.0.3.0/24",
                "security_group": "sg-abc123",
                "cpu_utilization": 35,  # DB is actually fine
                "connections": 15,  # Low because apps can't connect
                "max_connections": 500
            }
        }

        # Security groups (THE PROBLEM)
        self.security_groups = {
            "sg-abc123": {
                "id": "sg-abc123",
                "name": "rds-security-group",
                "description": "Security group for RDS database",
                "vpc_id": "vpc-main",
                "inbound_rules": [
                    {
                        "port": 5432,
                        "protocol": "tcp",
                        "source": "10.0.1.0/24",  # Only admin subnet, NOT app subnet!
                        "description": "Allow PostgreSQL from app subnet only"
                    }
                ],
                "outbound_rules": [
                    {
                        "port": -1,
                        "protocol": "-1",
                        "destination": "0.0.0.0/0",
                        "description": "Allow all outbound"
                    }
                ]
            },
            "sg-app-tier": {
                "id": "sg-app-tier",
                "name": "app-tier-security-group",
                "description": "Security group for application tier",
                "vpc_id": "vpc-main",
                "inbound_rules": [
                    {
                        "port": 80,
                        "protocol": "tcp",
                        "source": "0.0.0.0/0",
                        "description": "Allow HTTP from anywhere"
                    },
                    {
                        "port": 443,
                        "protocol": "tcp",
                        "source": "0.0.0.0/0",
                        "description": "Allow HTTPS from anywhere"
                    }
                ],
                "outbound_rules": [
                    {
                        "port": -1,
                        "protocol": "-1",
                        "destination": "0.0.0.0/0",
                        "description": "Allow all outbound"
                    }
                ]
            }
        }

        # Change history (THE ROOT CAUSE)
        self.change_history = [
            {
                "timestamp": "2024-01-15T08:15:00Z",
                "change_id": "CHG-2024-0115-001",
                "change_type": "security_group_modification",
                "resource_type": "security_group",
                "resource_id": "sg-abc123",
                "user": "admin@company.com",
                "description": "Modified inbound rules for RDS security group",
                "details": {
                    "before": {
                        "rules": [
                            {
                                "port": 5432,
                                "protocol": "tcp",
                                "source": "10.0.0.0/16",
                                "description": "Allow PostgreSQL from VPC"
                            }
                        ]
                    },
                    "after": {
                        "rules": [
                            {
                                "port": 5432,
                                "protocol": "tcp",
                                "source": "10.0.1.0/24",
                                "description": "Allow PostgreSQL from app subnet only"
                            }
                        ]
                    }
                },
                "reason": "Tighten security - limit database access to specific subnet"
            },
            {
                "timestamp": "2024-01-10T14:00:00Z",
                "change_id": "CHG-2024-0110-003",
                "change_type": "code_deployment",
                "resource_type": "application",
                "resource_id": "payment-service",
                "user": "ci-cd-pipeline",
                "description": "Deployed version v2.3.1 of payment-service",
                "details": {
                    "version": "v2.3.1",
                    "changes": ["Bug fixes for payment validation", "Updated logging configuration"]
                },
                "reason": "Routine deployment - bug fixes only, no performance changes expected"
            },
            {
                "timestamp": "2024-01-08T16:30:00Z",
                "change_id": "CHG-2024-0108-007",
                "change_type": "infrastructure_scaling",
                "resource_type": "ec2",
                "resource_id": "payment-service",
                "user": "devops@company.com",
                "description": "Scaled payment-service from 2 to 3 instances",
                "details": {
                    "previous_count": 2,
                    "new_count": 3,
                    "instance_type": "m5.xlarge"
                },
                "reason": "Proactive capacity increase for expected traffic growth"
            }
        ]

        # Network topology
        self.network_topology = {
            "vpc_id": "vpc-main",
            "vpc_cidr": "10.0.0.0/16",
            "subnets": {
                "admin": {
                    "cidr": "10.0.1.0/24",
                    "availability_zone": "us-east-1a",
                    "resources": ["bastion-host", "vpn-gateway"]
                },
                "app_tier": {
                    "cidr": "10.0.2.0/24",
                    "availability_zone": "us-east-1b",
                    "resources": ["payment-service instances"]
                },
                "database_tier": {
                    "cidr": "10.0.3.0/24",
                    "availability_zone": "us-east-1c",
                    "resources": ["prod-payment-db"]
                }
            },
            "route_tables": {
                "public": ["admin", "app_tier"],
                "private": ["database_tier"]
            }
        }

        # Application logs (showing connection errors)
        self.application_logs = [
            {
                "timestamp": "2024-01-15T10:04:45Z",
                "level": "ERROR",
                "service": "payment-service",
                "instance": "i-abc123",
                "message": "DatabaseConnectionTimeout: Unable to connect to prod-payment-db.cluster-xyz.us-east-1.rds.amazonaws.com:5432",
                "details": "Connection attempt 3 of 3 failed. Timeout after 10 seconds."
            },
            {
                "timestamp": "2024-01-15T10:04:30Z",
                "level": "WARN",
                "service": "payment-service",
                "instance": "i-abc124",
                "message": "Database connection retry attempt 2",
                "details": "Previous connection attempt failed with timeout"
            },
            {
                "timestamp": "2024-01-15T10:04:15Z",
                "level": "ERROR",
                "service": "payment-service",
                "instance": "i-abc125",
                "message": "DatabaseConnectionTimeout: Connection to database failed",
                "details": "Network timeout - no route to host"
            }
        ]

        # Tool call log for evaluation
        self.tool_call_log = []

        # Actions taken (for tracking remediation)
        self.actions_taken = []

    def log_tool_call(self, tool_name: str, parameters: Dict[str, Any] = None):
        """Log a tool call for evaluation."""
        self.tool_call_log.append({
            "tool": tool_name,
            "params": parameters or {},
            "timestamp": datetime.now().isoformat()
        })

    def get_tool_call_log(self) -> List[Dict[str, Any]]:
        """Return all tool calls made."""
        return self.tool_call_log

    def get_service_metrics(self, service_name: str, metric_type: str,
                           timerange: str = "1h") -> Dict[str, Any]:
        """Get performance metrics for a service.

        Parameters:
        - service_name: Name of the service (e.g., 'payment-service')
        - metric_type: Type of metric ('response_time', 'error_rate', 'cpu', 'memory', 'network', 'connections')
        - timerange: Time range for metrics (default: '1h')
        """
        self.log_tool_call("get_service_metrics", {
            "service_name": service_name,
            "metric_type": metric_type,
            "timerange": timerange
        })

        if service_name not in self.metrics:
            return {"error": f"Service {service_name} not found"}

        metrics = self.metrics[service_name]

        if metric_type == "response_time":
            return {
                "service": service_name,
                "metric": "response_time",
                "timerange": timerange,
                "avg_response_time_seconds": metrics["avg_response_time"],
                "p95_response_time_seconds": metrics["p95_response_time"],
                "p99_response_time_seconds": metrics["p99_response_time"],
                "degradation_start_time": "2024-01-15T08:20:00Z"
            }
        elif metric_type == "error_rate":
            return {
                "service": service_name,
                "metric": "error_rate",
                "timerange": timerange,
                "current_error_rate_percent": metrics["error_rate"],
                "error_types": {
                    "DatabaseConnectionTimeout": 95,  # THE SMOKING GUN
                    "ValidationError": 3,
                    "Other": 2
                },
                "spike_start_time": "2024-01-15T08:30:00Z"
            }
        elif metric_type == "cpu":
            return {
                "service": service_name,
                "metric": "cpu_utilization",
                "timerange": timerange,
                "avg_cpu_percent": metrics["cpu_utilization"],
                "peak_cpu_percent": 92,
                "spike_start_time": "2024-01-15T08:25:00Z"
            }
        elif metric_type == "memory":
            return {
                "service": service_name,
                "metric": "memory_utilization",
                "timerange": timerange,
                "avg_memory_percent": metrics["memory_utilization"],
                "peak_memory_percent": 78
            }
        elif metric_type == "network":
            return {
                "service": service_name,
                "metric": "network",
                "timerange": timerange,
                "network_in_mbps": metrics["network_in"],
                "network_out_mbps": metrics["network_out"]
            }
        elif metric_type == "connections":
            return {
                "service": service_name,
                "metric": "connections",
                "timerange": timerange,
                "active_connections": metrics["active_connections"],
                "failed_connections": metrics["failed_connections"],  # KEY METRIC
                "connection_timeout_errors": 180,
                "pattern": "Failed connections increased sharply at 08:20 AM"
            }
        else:
            return {"error": f"Unknown metric type: {metric_type}"}

    def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get basic information about a service.

        Parameters:
        - service_name: Name of the service
        """
        self.log_tool_call("get_service_info", {"service_name": service_name})

        if service_name not in self.services:
            return {"error": f"Service {service_name} not found"}

        return self.services[service_name]

    def get_recent_changes(self, timerange: str = "7d",
                          resource_type: Optional[str] = None) -> str:
        """Get recent infrastructure/configuration changes.

        Parameters:
        - timerange: How far back to look (e.g., '7d', '24h')
        - resource_type: Filter by type ('security_group', 'application', 'infrastructure', or None for all)
        """
        self.log_tool_call("get_recent_changes", {
            "timerange": timerange,
            "resource_type": resource_type
        })

        changes = self.change_history

        if resource_type:
            changes = [c for c in changes if c["change_type"].startswith(resource_type)]

        # Format as readable text instead of returning raw dict
        if not changes:
            return "No recent changes found in the specified timerange."

        result = f"Recent Changes (last {timerange}):\n\n"
        for i, change in enumerate(changes, 1):
            result += f"{i}. {change['change_type'].upper()} at {change['timestamp']}\n"
            result += f"   Resource: {change['resource_id']} ({change['resource_type']})\n"
            result += f"   User: {change['user']}\n"
            result += f"   Description: {change['description']}\n"

            if change['change_type'] == 'security_group_modification':
                before = change['details']['before']['rules'][0]
                after = change['details']['after']['rules'][0]
                result += f"   BEFORE: Port {before['port']} from {before['source']}\n"
                result += f"   AFTER: Port {after['port']} from {after['source']}\n"
                result += f"   Impact: Changed from allowing {before['source']} to only {after['source']}\n"

            result += f"   Reason: {change['reason']}\n\n"

        return result

    def get_security_group_details(self, security_group_id: str) -> Dict[str, Any]:
        """Get detailed configuration of a security group.

        Parameters:
        - security_group_id: ID of the security group (e.g., 'sg-abc123')
        """
        self.log_tool_call("get_security_group_details", {
            "security_group_id": security_group_id
        })

        if security_group_id not in self.security_groups:
            return {"error": f"Security group {security_group_id} not found"}

        return self.security_groups[security_group_id]

    def check_network_connectivity(self, source: str, destination: str,
                                  port: int) -> Dict[str, Any]:
        """Check if network connectivity exists between source and destination.

        Parameters:
        - source: Source CIDR or subnet name (e.g., '10.0.2.0/24', 'app_tier')
        - destination: Destination resource or subnet (e.g., 'prod-payment-db', 'database_tier')
        - port: Port number to check
        """
        self.log_tool_call("check_network_connectivity", {
            "source": source,
            "destination": destination,
            "port": port
        })

        # Map names to CIDRs
        source_cidr = source
        if source == "app_tier" or source == "payment-service":
            source_cidr = "10.0.2.0/24"
        elif source == "admin":
            source_cidr = "10.0.1.0/24"

        # Check if port 5432 from app tier to database
        if port == 5432 and "10.0.2" in source_cidr:
            # This is THE KEY CHECK that should reveal the problem
            db_sg = self.security_groups["sg-abc123"]
            allowed_sources = [rule["source"] for rule in db_sg["inbound_rules"] if rule["port"] == 5432]

            # Check if source_cidr matches any allowed source
            allowed = False
            for allowed_source in allowed_sources:
                if allowed_source == source_cidr or allowed_source == "10.0.0.0/16":
                    allowed = True
                    break

            return {
                "source": source_cidr,
                "destination": destination,
                "port": port,
                "connectivity": "BLOCKED" if not allowed else "ALLOWED",
                "reason": f"Security group sg-abc123 only allows {allowed_sources}, does not include {source_cidr}" if not allowed else "Connection allowed",
                "security_group": "sg-abc123",
                "recommendation": f"Update sg-abc123 to allow port {port} from {source_cidr}" if not allowed else None
            }

        return {
            "source": source,
            "destination": destination,
            "port": port,
            "connectivity": "ALLOWED",
            "reason": "No restrictions found"
        }

    def get_application_logs(self, service_name: str, level: str = None,
                           timerange: str = "1h", limit: int = 10) -> List[Dict[str, Any]]:
        """Get application logs for a service.

        Parameters:
        - service_name: Name of the service
        - level: Log level filter ('ERROR', 'WARN', 'INFO', or None for all)
        - timerange: Time range for logs
        - limit: Maximum number of log entries to return
        """
        self.log_tool_call("get_application_logs", {
            "service_name": service_name,
            "level": level,
            "timerange": timerange,
            "limit": limit
        })

        logs = [log for log in self.application_logs if log["service"] == service_name]

        if level:
            logs = [log for log in logs if log["level"] == level]

        return logs[:limit]

    def get_database_metrics(self, database_name: str) -> Dict[str, Any]:
        """Get database performance metrics.

        Parameters:
        - database_name: Name of the database
        """
        self.log_tool_call("get_database_metrics", {"database_name": database_name})

        if database_name not in self.databases:
            return {"error": f"Database {database_name} not found"}

        db = self.databases[database_name]
        return {
            "database": database_name,
            "cpu_utilization_percent": db["cpu_utilization"],
            "active_connections": db["connections"],
            "max_connections": db["max_connections"],
            "connection_utilization_percent": (db["connections"] / db["max_connections"]) * 100,
            "status": "healthy",
            "note": "Database itself is healthy - low CPU and low connection count suggests clients cannot connect"
        }

    def get_network_topology(self, vpc_id: str = "vpc-main") -> Dict[str, Any]:
        """Get VPC network topology information.

        Parameters:
        - vpc_id: VPC ID to query
        """
        self.log_tool_call("get_network_topology", {"vpc_id": vpc_id})

        return self.network_topology

    def correlate_events(self, event1_time: str, event2_time: str) -> str:
        """Correlate timing between two events to identify causal relationships.

        Parameters:
        - event1_time: Timestamp of first event (ISO format)
        - event2_time: Timestamp of second event (ISO format)
        """
        self.log_tool_call("correlate_events", {
            "event1_time": event1_time,
            "event2_time": event2_time
        })

        t1 = datetime.fromisoformat(event1_time.replace('Z', '+00:00'))
        t2 = datetime.fromisoformat(event2_time.replace('Z', '+00:00'))

        delta = abs((t2 - t1).total_seconds() / 60)  # minutes
        correlation_strength = "HIGH" if delta < 10 else "MEDIUM" if delta < 30 else "LOW"

        analysis = f"Events occurred {delta:.1f} minutes apart. "
        if delta < 10:
            analysis += "Strong temporal correlation suggests potential causal relationship."
        elif delta < 30:
            analysis += "Moderate temporal proximity - may be related."
        else:
            analysis += "Weak temporal correlation - likely unrelated."

        return f"""Temporal Correlation Analysis:
Event 1: {event1_time}
Event 2: {event2_time}
Time Difference: {delta:.1f} minutes
Correlation Strength: {correlation_strength}

Analysis: {analysis}"""

    def scale_service(self, service_name: str, target_count: int,
                     reason: str) -> Dict[str, Any]:
        """Scale service instances (WRONG SOLUTION for this scenario).

        Parameters:
        - service_name: Name of the service to scale
        - target_count: Desired number of instances
        - reason: Justification for scaling
        """
        self.log_tool_call("scale_service", {
            "service_name": service_name,
            "target_count": target_count,
            "reason": reason
        })

        if service_name not in self.services:
            return {"error": f"Service {service_name} not found"}

        service = self.services[service_name]
        previous_count = service["instance_count"]
        added_instances = target_count - previous_count

        # Update state
        service["instance_count"] = target_count
        if added_instances > 0:
            for i in range(added_instances):
                new_instance_id = f"i-abc{126 + i}"
                service["instances"].append(new_instance_id)

        self.actions_taken.append({
            "action": "scale_service",
            "service": service_name,
            "previous_count": previous_count,
            "new_count": target_count,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

        # This is wrong solution - new instances will have same connectivity problem
        return {
            "status": "SUCCESS",
            "service": service_name,
            "previous_count": previous_count,
            "new_count": target_count,
            "instances_added": added_instances,
            "new_instance_ids": service["instances"][-added_instances:] if added_instances > 0 else [],
            "estimated_cost_increase_per_month": added_instances * 800,
            "warning": "New instances deployed but connectivity issues may persist if root cause is not addressed"
        }

    def update_security_group(self, security_group_id: str,
                             action: str, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Update security group rules (CORRECT SOLUTION).

        Parameters:
        - security_group_id: ID of security group to update
        - action: 'add_inbound' or 'remove_inbound'
        - rule: Rule specification (port, protocol, source, description)
        """
        self.log_tool_call("update_security_group", {
            "security_group_id": security_group_id,
            "action": action,
            "rule": rule
        })

        if security_group_id not in self.security_groups:
            return {"error": f"Security group {security_group_id} not found"}

        sg = self.security_groups[security_group_id]

        if action == "add_inbound":
            sg["inbound_rules"].append(rule)
        elif action == "remove_inbound":
            sg["inbound_rules"] = [r for r in sg["inbound_rules"]
                                  if not (r["port"] == rule["port"] and r["source"] == rule["source"])]

        # If fixing the database security group to allow app tier access
        if security_group_id == "sg-abc123" and any(r["source"] in ["10.0.2.0/24", "10.0.0.0/16"]
                                                      for r in sg["inbound_rules"] if r["port"] == 5432):
            # FIX APPLIED - update metrics to show improvement
            self.metrics["payment-service"]["error_rate"] = 0.8
            self.metrics["payment-service"]["avg_response_time"] = 1.5
            self.metrics["payment-service"]["cpu_utilization"] = 45
            self.metrics["payment-service"]["failed_connections"] = 0
            self.databases["prod-payment-db"]["connections"] = 45

        self.actions_taken.append({
            "action": "update_security_group",
            "security_group_id": security_group_id,
            "rule_action": action,
            "rule": rule,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "status": "SUCCESS",
            "security_group_id": security_group_id,
            "action": action,
            "rule_applied": rule,
            "current_inbound_rules": sg["inbound_rules"]
        }

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state of the environment for evaluation."""
        return {
            "services": self.services,
            "metrics": self.metrics,
            "databases": self.databases,
            "security_groups": self.security_groups,
            "actions_taken": self.actions_taken,
            "problem_resolved": self.metrics["payment-service"]["error_rate"] < 1.0
        }
