"""
Schema Compliance Monitor for Structr

Tracks schema compliance over time, detects trends, and provides alerts
when products become non-compliant with Google Product Schema requirements.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading
import time
from dataclasses import dataclass, asdict
from enum import Enum

from config import CONFIG
from validators.schema_validator import validate_all_bundles, validate_single_bundle


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceStatus(Enum):
    """Compliance status levels"""
    EXCELLENT = "excellent"
    GOOD = "good" 
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class ComplianceRecord:
    """Individual compliance measurement record"""
    bundle_id: str
    timestamp: datetime
    compliance_score: float
    google_eligible: bool
    schema_found: bool
    required_fields_passed: int
    required_fields_total: int
    recommended_fields_passed: int
    recommended_fields_total: int
    offers_fields_passed: int
    offers_fields_total: int
    total_issues: int
    critical_issues: int
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplianceRecord':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class AlertRule:
    """Alert rule configuration"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    enabled: bool
    conditions: Dict[str, Any]
    notification_channels: List[str]
    cooldown_minutes: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRule':
        """Create from dictionary"""
        data['severity'] = AlertSeverity(data['severity'])
        return cls(**data)


@dataclass
class Alert:
    """Active alert"""
    id: str
    rule_id: str
    bundle_id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    resolved_timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_timestamp:
            data['resolved_timestamp'] = self.resolved_timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create from dictionary"""
        data['severity'] = AlertSeverity(data['severity'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('resolved_timestamp'):
            data['resolved_timestamp'] = datetime.fromisoformat(data['resolved_timestamp'])
        return cls(**data)


class ComplianceMonitor:
    """Main compliance monitoring system"""
    
    def __init__(self):
        self.monitoring_dir = CONFIG.get_monitoring_dir()
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.monitoring_dir / "compliance_monitor.db"
        self.alerts_file = self.monitoring_dir / "active_alerts.json"
        self.rules_file = self.monitoring_dir / "alert_rules.json"
        self.config_file = self.monitoring_dir / "monitor_config.json"
        
        self._init_database()
        self._load_alert_rules()
        self._load_monitor_config()
        self.active_alerts: List[Alert] = self._load_active_alerts()
        
        self._monitoring_thread = None
        self._stop_monitoring = False
    
    def _init_database(self):
        """Initialize SQLite database for compliance history"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bundle_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    compliance_score REAL NOT NULL,
                    google_eligible BOOLEAN NOT NULL,
                    schema_found BOOLEAN NOT NULL,
                    required_fields_passed INTEGER NOT NULL,
                    required_fields_total INTEGER NOT NULL,
                    recommended_fields_passed INTEGER NOT NULL,
                    recommended_fields_total INTEGER NOT NULL,
                    offers_fields_passed INTEGER NOT NULL,
                    offers_fields_total INTEGER NOT NULL,
                    total_issues INTEGER NOT NULL,
                    critical_issues INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_bundle_timestamp 
                ON compliance_history(bundle_id, timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON compliance_history(timestamp)
            """)
    
    def _load_alert_rules(self):
        """Load alert rules from configuration"""
        
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r') as f:
                    rules_data = json.load(f)
                self.alert_rules = [AlertRule.from_dict(rule) for rule in rules_data]
            except Exception as e:
                print(f"Error loading alert rules: {e}")
                self.alert_rules = self._get_default_alert_rules()
        else:
            self.alert_rules = self._get_default_alert_rules()
            self._save_alert_rules()
    
    def _get_default_alert_rules(self) -> List[AlertRule]:
        """Get default alert rules"""
        
        return [
            AlertRule(
                id="compliance_drop_critical",
                name="Critical Compliance Drop",
                description="Alert when compliance drops below critical threshold",
                severity=AlertSeverity.CRITICAL,
                enabled=True,
                conditions={
                    "compliance_score_below": 40,
                    "google_eligible": False,
                    "critical_issues_above": 3
                },
                notification_channels=["dashboard", "email"],
                cooldown_minutes=30
            ),
            AlertRule(
                id="compliance_drop_high",
                name="High Compliance Drop",
                description="Alert when compliance drops below good threshold",
                severity=AlertSeverity.HIGH,
                enabled=True,
                conditions={
                    "compliance_score_below": CONFIG.SCORE_THRESHOLDS['good'],
                    "decline_over_hours": 24,
                    "decline_percentage": 20
                },
                notification_channels=["dashboard"],
                cooldown_minutes=60
            ),
            AlertRule(
                id="google_eligibility_lost",
                name="Google Eligibility Lost",
                description="Alert when product loses Google Rich Results eligibility",
                severity=AlertSeverity.HIGH,
                enabled=True,
                conditions={
                    "google_eligible": False,
                    "was_google_eligible": True
                },
                notification_channels=["dashboard", "email"],
                cooldown_minutes=15
            ),
            AlertRule(
                id="schema_not_found",
                name="Schema Not Found",
                description="Alert when product schema becomes undetectable",
                severity=AlertSeverity.MEDIUM,
                enabled=True,
                conditions={
                    "schema_found": False,
                    "had_schema": True
                },
                notification_channels=["dashboard"],
                cooldown_minutes=120
            ),
            AlertRule(
                id="compliance_trend_declining",
                name="Declining Compliance Trend",
                description="Alert when compliance shows declining trend over time",
                severity=AlertSeverity.MEDIUM,
                enabled=True,
                conditions={
                    "trend_declining": True,
                    "trend_duration_hours": 48,
                    "trend_decline_percentage": 15
                },
                notification_channels=["dashboard"],
                cooldown_minutes=360
            )
        ]
    
    def _save_alert_rules(self):
        """Save alert rules to configuration"""
        
        try:
            with open(self.rules_file, 'w') as f:
                json.dump([rule.to_dict() for rule in self.alert_rules], f, indent=2)
        except Exception as e:
            print(f"Error saving alert rules: {e}")
    
    def _load_monitor_config(self):
        """Load monitoring configuration"""
        
        default_config = {
            "monitoring_enabled": True,
            "check_interval_minutes": 60,
            "retention_days": 90,
            "email_notifications": {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_emails": []
            },
            "webhook_notifications": {
                "enabled": False,
                "urls": []
            },
            "alert_thresholds": {
                "compliance_score_critical": 40,
                "compliance_score_warning": CONFIG.SCORE_THRESHOLDS['good'],
                "max_critical_issues": 3,
                "max_total_issues": 10
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config = {**default_config, **json.load(f)}
            except Exception as e:
                print(f"Error loading monitor config: {e}")
                self.config = default_config
        else:
            self.config = default_config
            self._save_monitor_config()
    
    def _save_monitor_config(self):
        """Save monitoring configuration"""
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving monitor config: {e}")
    
    def _load_active_alerts(self) -> List[Alert]:
        """Load active alerts"""
        
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r') as f:
                    alerts_data = json.load(f)
                return [Alert.from_dict(alert) for alert in alerts_data]
            except Exception as e:
                print(f"Error loading active alerts: {e}")
        
        return []
    
    def _save_active_alerts(self):
        """Save active alerts"""
        
        try:
            with open(self.alerts_file, 'w') as f:
                json.dump([alert.to_dict() for alert in self.active_alerts], f, indent=2)
        except Exception as e:
            print(f"Error saving active alerts: {e}")
    
    def record_compliance(self, validation_results: List[Dict[str, Any]]):
        """Record compliance measurements for all bundles"""
        
        timestamp = datetime.now()
        records = []
        
        for result in validation_results:
            if not result.get('schema_found', False):
                # Still record non-schema bundles for trend tracking
                record = ComplianceRecord(
                    bundle_id=result.get('bundle_id', 'unknown'),
                    timestamp=timestamp,
                    compliance_score=0.0,
                    google_eligible=False,
                    schema_found=False,
                    required_fields_passed=0,
                    required_fields_total=5,  # Default expected fields
                    recommended_fields_passed=0,
                    recommended_fields_total=5,
                    offers_fields_passed=0,
                    offers_fields_total=3,
                    total_issues=0,
                    critical_issues=0,
                    status="no_schema"
                )
            else:
                summary = result.get('summary', {})
                compliance_score = result.get('compliance_score', 0)
                
                # Determine status
                if compliance_score >= CONFIG.SCORE_THRESHOLDS['excellent']:
                    status = ComplianceStatus.EXCELLENT.value
                elif compliance_score >= CONFIG.SCORE_THRESHOLDS['good']:
                    status = ComplianceStatus.GOOD.value
                elif compliance_score >= CONFIG.SCORE_THRESHOLDS['fair']:
                    status = ComplianceStatus.FAIR.value
                elif compliance_score >= 20:
                    status = ComplianceStatus.POOR.value
                else:
                    status = ComplianceStatus.CRITICAL.value
                
                record = ComplianceRecord(
                    bundle_id=result.get('bundle_id', 'unknown'),
                    timestamp=timestamp,
                    compliance_score=compliance_score,
                    google_eligible=result.get('google_eligible', False),
                    schema_found=True,
                    required_fields_passed=summary.get('required_passed', 0),
                    required_fields_total=summary.get('required_total', 5),
                    recommended_fields_passed=summary.get('recommended_passed', 0),
                    recommended_fields_total=summary.get('recommended_total', 5),
                    offers_fields_passed=summary.get('offers_passed', 0),
                    offers_fields_total=summary.get('offers_total', 3),
                    total_issues=summary.get('total_issues', 0),
                    critical_issues=summary.get('critical_issues', 0),
                    status=status
                )
            
            records.append(record)
        
        # Store in database
        self._store_records(records)
        
        # Check for alerts
        self._check_alert_conditions(records)
        
        return records
    
    def _store_records(self, records: List[ComplianceRecord]):
        """Store compliance records in database"""
        
        with sqlite3.connect(self.db_path) as conn:
            for record in records:
                conn.execute("""
                    INSERT INTO compliance_history (
                        bundle_id, timestamp, compliance_score, google_eligible, schema_found,
                        required_fields_passed, required_fields_total,
                        recommended_fields_passed, recommended_fields_total,
                        offers_fields_passed, offers_fields_total,
                        total_issues, critical_issues, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.bundle_id,
                    record.timestamp.isoformat(),
                    record.compliance_score,
                    record.google_eligible,
                    record.schema_found,
                    record.required_fields_passed,
                    record.required_fields_total,
                    record.recommended_fields_passed,
                    record.recommended_fields_total,
                    record.offers_fields_passed,
                    record.offers_fields_total,
                    record.total_issues,
                    record.critical_issues,
                    record.status
                ))
    
    def _check_alert_conditions(self, current_records: List[ComplianceRecord]):
        """Check alert conditions against current and historical data"""
        
        for record in current_records:
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # Check if alert already exists and is in cooldown
                if self._is_alert_in_cooldown(rule.id, record.bundle_id):
                    continue
                
                # Evaluate rule conditions
                if self._evaluate_alert_rule(rule, record):
                    alert = self._create_alert(rule, record)
                    self.active_alerts.append(alert)
                    self._notify_alert(alert)
        
        self._save_active_alerts()
    
    def _is_alert_in_cooldown(self, rule_id: str, bundle_id: str) -> bool:
        """Check if alert is in cooldown period"""
        
        cutoff_time = datetime.now() - timedelta(minutes=60)  # Default cooldown
        
        for rule in self.alert_rules:
            if rule.id == rule_id:
                cutoff_time = datetime.now() - timedelta(minutes=rule.cooldown_minutes)
                break
        
        for alert in self.active_alerts:
            if (alert.rule_id == rule_id and 
                alert.bundle_id == bundle_id and 
                alert.timestamp > cutoff_time and
                not alert.resolved):
                return True
        
        return False
    
    def _evaluate_alert_rule(self, rule: AlertRule, record: ComplianceRecord) -> bool:
        """Evaluate if alert rule conditions are met"""
        
        conditions = rule.conditions
        
        # Simple condition checks
        if "compliance_score_below" in conditions:
            if record.compliance_score >= conditions["compliance_score_below"]:
                return False
        
        if "google_eligible" in conditions:
            if record.google_eligible != conditions["google_eligible"]:
                return False
        
        if "schema_found" in conditions:
            if record.schema_found != conditions["schema_found"]:
                return False
        
        if "critical_issues_above" in conditions:
            if record.critical_issues <= conditions["critical_issues_above"]:
                return False
        
        # Historical condition checks
        if "was_google_eligible" in conditions:
            if not self._was_previously_google_eligible(record.bundle_id):
                return False
        
        if "had_schema" in conditions:
            if not self._previously_had_schema(record.bundle_id):
                return False
        
        if "decline_over_hours" in conditions and "decline_percentage" in conditions:
            if not self._check_compliance_decline(
                record.bundle_id,
                conditions["decline_over_hours"],
                conditions["decline_percentage"]
            ):
                return False
        
        if "trend_declining" in conditions:
            if not self._check_declining_trend(
                record.bundle_id,
                conditions.get("trend_duration_hours", 48),
                conditions.get("trend_decline_percentage", 15)
            ):
                return False
        
        return True
    
    def _was_previously_google_eligible(self, bundle_id: str) -> bool:
        """Check if bundle was previously Google eligible"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT google_eligible FROM compliance_history 
                WHERE bundle_id = ? AND google_eligible = 1
                ORDER BY timestamp DESC LIMIT 1
            """, (bundle_id,))
            
            return cursor.fetchone() is not None
    
    def _previously_had_schema(self, bundle_id: str) -> bool:
        """Check if bundle previously had schema"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT schema_found FROM compliance_history 
                WHERE bundle_id = ? AND schema_found = 1
                ORDER BY timestamp DESC LIMIT 1
            """, (bundle_id,))
            
            return cursor.fetchone() is not None
    
    def _check_compliance_decline(self, bundle_id: str, hours: int, percentage: float) -> bool:
        """Check if compliance has declined by percentage over time period"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT compliance_score FROM compliance_history 
                WHERE bundle_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC LIMIT 1
            """, (bundle_id, cutoff_time.isoformat()))
            
            old_record = cursor.fetchone()
            if not old_record:
                return False
            
            cursor = conn.execute("""
                SELECT compliance_score FROM compliance_history 
                WHERE bundle_id = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (bundle_id,))
            
            new_record = cursor.fetchone()
            if not new_record:
                return False
            
            old_score, new_score = old_record[0], new_record[0]
            
            if old_score == 0:
                return False
            
            decline_pct = ((old_score - new_score) / old_score) * 100
            return decline_pct >= percentage
    
    def _check_declining_trend(self, bundle_id: str, hours: int, decline_percentage: float) -> bool:
        """Check if there's a declining trend over time period"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT compliance_score, timestamp FROM compliance_history 
                WHERE bundle_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (bundle_id, cutoff_time.isoformat()))
            
            records = cursor.fetchall()
            
            if len(records) < 3:  # Need at least 3 points for trend
                return False
            
            # Simple trend analysis - check if recent scores are consistently lower
            scores = [record[0] for record in records]
            
            # Compare first third vs last third
            first_third = scores[:len(scores)//3]
            last_third = scores[-len(scores)//3:]
            
            avg_first = sum(first_third) / len(first_third)
            avg_last = sum(last_third) / len(last_third)
            
            if avg_first == 0:
                return False
            
            decline_pct = ((avg_first - avg_last) / avg_first) * 100
            return decline_pct >= decline_percentage
    
    def _create_alert(self, rule: AlertRule, record: ComplianceRecord) -> Alert:
        """Create alert from rule and record"""
        
        alert_id = f"{rule.id}_{record.bundle_id}_{int(record.timestamp.timestamp())}"
        
        # Generate alert message based on rule
        if rule.id == "compliance_drop_critical":
            title = f"Critical Compliance Drop: {record.bundle_id}"
            message = f"Product '{record.bundle_id}' compliance dropped to {record.compliance_score:.1f}% with {record.critical_issues} critical issues"
        elif rule.id == "google_eligibility_lost":
            title = f"Google Eligibility Lost: {record.bundle_id}"
            message = f"Product '{record.bundle_id}' is no longer eligible for Google Rich Results"
        elif rule.id == "schema_not_found":
            title = f"Schema Not Found: {record.bundle_id}"
            message = f"Product '{record.bundle_id}' schema is no longer detectable"
        elif rule.id == "compliance_trend_declining":
            title = f"Declining Trend: {record.bundle_id}"
            message = f"Product '{record.bundle_id}' shows declining compliance trend"
        else:
            title = f"Compliance Alert: {record.bundle_id}"
            message = f"Product '{record.bundle_id}' triggered alert rule '{rule.name}'"
        
        return Alert(
            id=alert_id,
            rule_id=rule.id,
            bundle_id=record.bundle_id,
            severity=rule.severity,
            title=title,
            message=message,
            timestamp=record.timestamp
        )
    
    def _notify_alert(self, alert: Alert):
        """Send alert notifications"""
        
        # Find the rule for notification channels
        rule = next((r for r in self.alert_rules if r.id == alert.rule_id), None)
        if not rule:
            return
        
        for channel in rule.notification_channels:
            if channel == "dashboard":
                # Dashboard notifications are handled by active_alerts list
                pass
            elif channel == "email" and self.config["email_notifications"]["enabled"]:
                self._send_email_notification(alert)
            elif channel == "webhook" and self.config["webhook_notifications"]["enabled"]:
                self._send_webhook_notification(alert)
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification (placeholder)"""
        # TODO: Implement email sending
        print(f"EMAIL ALERT: {alert.title} - {alert.message}")
    
    def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification (placeholder)"""
        # TODO: Implement webhook sending
        print(f"WEBHOOK ALERT: {alert.title} - {alert.message}")
    
    def get_compliance_history(self, bundle_id: Optional[str] = None, 
                             days: int = 30) -> List[ComplianceRecord]:
        """Get compliance history for bundle(s)"""
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            if bundle_id:
                cursor = conn.execute("""
                    SELECT * FROM compliance_history 
                    WHERE bundle_id = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                """, (bundle_id, cutoff_time.isoformat()))
            else:
                cursor = conn.execute("""
                    SELECT * FROM compliance_history 
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (cutoff_time.isoformat(),))
            
            records = []
            for row in cursor.fetchall():
                record = ComplianceRecord(
                    bundle_id=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    compliance_score=row[3],
                    google_eligible=bool(row[4]),
                    schema_found=bool(row[5]),
                    required_fields_passed=row[6],
                    required_fields_total=row[7],
                    recommended_fields_passed=row[8],
                    recommended_fields_total=row[9],
                    offers_fields_passed=row[10],
                    offers_fields_total=row[11],
                    total_issues=row[12],
                    critical_issues=row[13],
                    status=row[14]
                )
                records.append(record)
            
            return records
    
    def get_compliance_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get compliance summary statistics"""
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get latest record for each bundle
            cursor = conn.execute("""
                WITH latest_records AS (
                    SELECT bundle_id, MAX(timestamp) as max_timestamp
                    FROM compliance_history 
                    WHERE timestamp >= ?
                    GROUP BY bundle_id
                )
                SELECT ch.* FROM compliance_history ch
                INNER JOIN latest_records lr 
                ON ch.bundle_id = lr.bundle_id AND ch.timestamp = lr.max_timestamp
            """, (cutoff_time.isoformat(),))
            
            records = cursor.fetchall()
            
            if not records:
                return {
                    "total_bundles": 0,
                    "google_eligible": 0,
                    "avg_compliance_score": 0,
                    "critical_alerts": 0,
                    "schema_found_rate": 0,
                    "status_distribution": {}
                }
            
            total_bundles = len(records)
            google_eligible = sum(1 for r in records if r[4])  # google_eligible column
            avg_score = sum(r[3] for r in records) / total_bundles  # compliance_score column
            schema_found = sum(1 for r in records if r[5])  # schema_found column
            
            # Count status distribution
            status_counts = {}
            for record in records:
                status = record[14]  # status column
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count critical alerts
            critical_alerts = len([a for a in self.active_alerts 
                                 if a.severity == AlertSeverity.CRITICAL and not a.resolved])
            
            return {
                "total_bundles": total_bundles,
                "google_eligible": google_eligible,
                "google_eligible_rate": google_eligible / total_bundles * 100,
                "avg_compliance_score": avg_score,
                "schema_found": schema_found,
                "schema_found_rate": schema_found / total_bundles * 100,
                "critical_alerts": critical_alerts,
                "total_active_alerts": len([a for a in self.active_alerts if not a.resolved]),
                "status_distribution": status_counts
            }
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self._save_active_alerts()
                return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_timestamp = datetime.now()
                self._save_active_alerts()
                return True
        
        return False
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return False
        
        self._stop_monitoring = False
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        
        self._stop_monitoring = True
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        
        while not self._stop_monitoring:
            try:
                if self.config["monitoring_enabled"]:
                    # Run compliance check
                    validation_results = validate_all_bundles()
                    self.record_compliance(validation_results)
                
                # Sleep for configured interval
                interval_seconds = self.config["check_interval_minutes"] * 60
                for _ in range(interval_seconds):
                    if self._stop_monitoring:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def cleanup_old_data(self):
        """Clean up old compliance data based on retention policy"""
        
        retention_days = self.config.get("retention_days", 90)
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM compliance_history 
                WHERE timestamp < ?
            """, (cutoff_time.isoformat(),))
            
            deleted_count = cursor.rowcount
            
        # Clean up resolved alerts older than 30 days
        alert_cutoff = datetime.now() - timedelta(days=30)
        self.active_alerts = [
            alert for alert in self.active_alerts
            if not (alert.resolved and alert.resolved_timestamp and 
                   alert.resolved_timestamp < alert_cutoff)
        ]
        self._save_active_alerts()
        
        return deleted_count


# Global monitor instance
_monitor_instance = None

def get_compliance_monitor() -> ComplianceMonitor:
    """Get global compliance monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ComplianceMonitor()
    return _monitor_instance