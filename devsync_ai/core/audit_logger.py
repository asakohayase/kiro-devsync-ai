"""
Audit Logging Module

Provides comprehensive audit logging for hook system operations,
configuration changes, and security events.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Configuration events
    CONFIG_CREATE = "config_create"
    CONFIG_UPDATE = "config_update"
    CONFIG_DELETE = "config_delete"
    CONFIG_VIEW = "config_view"
    
    # Hook events
    HOOK_CREATE = "hook_create"
    HOOK_UPDATE = "hook_update"
    HOOK_DELETE = "hook_delete"
    HOOK_EXECUTE = "hook_execute"
    HOOK_ENABLE = "hook_enable"
    HOOK_DISABLE = "hook_disable"
    
    # Security events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"
    
    # Team events
    TEAM_CREATE = "team_create"
    TEAM_UPDATE = "team_update"
    TEAM_DELETE = "team_delete"
    TEAM_MEMBER_ADD = "team_member_add"
    TEAM_MEMBER_REMOVE = "team_member_remove"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_PROCESSED = "webhook_processed"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    team_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    result: str  # "success", "failure", "error"
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for serialization."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Main audit logging class."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Set up audit-specific logger
        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Add file handler if log file specified
        if log_file:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
    
    def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event."""
        try:
            # Log to audit logger
            self.audit_logger.info(event.to_json())
            
            # Log to database if available
            self._store_to_database(event)
            
            # Log security events to main logger as well
            if event.event_type in [
                AuditEventType.AUTH_FAILURE,
                AuditEventType.ACCESS_DENIED,
                AuditEventType.SYSTEM_ERROR
            ]:
                self.logger.warning(f"Security event: {event.action} - {event.result}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging audit event: {e}")
            return False
    
    def _store_to_database(self, event: AuditEvent) -> bool:
        """Store audit event to database (placeholder for future implementation)."""
        # TODO: Implement database storage
        return True
    
    def log_configuration_change(
        self,
        user_id: str,
        team_id: str,
        action: str,
        config_type: str,
        config_id: Optional[str] = None,
        old_config: Optional[Dict[str, Any]] = None,
        new_config: Optional[Dict[str, Any]] = None,
        result: str = "success",
        ip_address: Optional[str] = None
    ) -> bool:
        """Log configuration change events."""
        event_type_map = {
            "create": AuditEventType.CONFIG_CREATE,
            "update": AuditEventType.CONFIG_UPDATE,
            "delete": AuditEventType.CONFIG_DELETE,
            "view": AuditEventType.CONFIG_VIEW
        }
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type_map.get(action, AuditEventType.CONFIG_UPDATE),
            severity=AuditSeverity.MEDIUM if action in ["create", "update", "delete"] else AuditSeverity.LOW,
            timestamp=datetime.now(),
            user_id=user_id,
            team_id=team_id,
            resource_type=config_type,
            resource_id=config_id,
            action=action,
            result=result,
            details={
                "config_type": config_type,
                "old_config": old_config,
                "new_config": new_config
            },
            ip_address=ip_address
        )
        
        return self.log_event(event)
    
    def log_hook_operation(
        self,
        user_id: str,
        team_id: str,
        action: str,
        hook_type: str,
        hook_id: Optional[str] = None,
        execution_result: Optional[Dict[str, Any]] = None,
        result: str = "success",
        ip_address: Optional[str] = None
    ) -> bool:
        """Log hook operation events."""
        event_type_map = {
            "create": AuditEventType.HOOK_CREATE,
            "update": AuditEventType.HOOK_UPDATE,
            "delete": AuditEventType.HOOK_DELETE,
            "execute": AuditEventType.HOOK_EXECUTE,
            "enable": AuditEventType.HOOK_ENABLE,
            "disable": AuditEventType.HOOK_DISABLE
        }
        
        severity = AuditSeverity.HIGH if action == "execute" else AuditSeverity.MEDIUM
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type_map.get(action, AuditEventType.HOOK_UPDATE),
            severity=severity,
            timestamp=datetime.now(),
            user_id=user_id,
            team_id=team_id,
            resource_type="hook",
            resource_id=hook_id,
            action=action,
            result=result,
            details={
                "hook_type": hook_type,
                "execution_result": execution_result
            },
            ip_address=ip_address
        )
        
        return self.log_event(event)
    
    def log_security_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        action: str,
        result: str,
        details: Dict[str, Any],
        severity: AuditSeverity = AuditSeverity.HIGH,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Log security-related events."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(),
            user_id=user_id,
            team_id=None,
            resource_type="security",
            resource_id=None,
            action=action,
            result=result,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return self.log_event(event)
    
    def log_webhook_event(
        self,
        webhook_source: str,
        event_type: str,
        result: str,
        processing_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Log webhook processing events."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.WEBHOOK_PROCESSED,
            severity=AuditSeverity.LOW if result == "success" else AuditSeverity.MEDIUM,
            timestamp=datetime.now(),
            user_id=None,
            team_id=None,
            resource_type="webhook",
            resource_id=None,
            action="process",
            result=result,
            details={
                "webhook_source": webhook_source,
                "event_type": event_type,
                "processing_time_ms": processing_time_ms,
                "error_message": error_message
            },
            ip_address=ip_address
        )
        
        return self.log_event(event)
    
    def log_team_operation(
        self,
        user_id: str,
        action: str,
        team_id: str,
        target_user_id: Optional[str] = None,
        role_changes: Optional[Dict[str, Any]] = None,
        result: str = "success",
        ip_address: Optional[str] = None
    ) -> bool:
        """Log team management operations."""
        event_type_map = {
            "create": AuditEventType.TEAM_CREATE,
            "update": AuditEventType.TEAM_UPDATE,
            "delete": AuditEventType.TEAM_DELETE,
            "add_member": AuditEventType.TEAM_MEMBER_ADD,
            "remove_member": AuditEventType.TEAM_MEMBER_REMOVE
        }
        
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type_map.get(action, AuditEventType.TEAM_UPDATE),
            severity=AuditSeverity.MEDIUM,
            timestamp=datetime.now(),
            user_id=user_id,
            team_id=team_id,
            resource_type="team",
            resource_id=team_id,
            action=action,
            result=result,
            details={
                "target_user_id": target_user_id,
                "role_changes": role_changes
            },
            ip_address=ip_address
        )
        
        return self.log_event(event)
    
    def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Retrieve audit trail with filtering options."""
        # TODO: Implement database query for audit trail retrieval
        # This is a placeholder for future implementation
        return []


class SecurityAuditLogger:
    """Specialized audit logger for security events."""
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def log_authentication_attempt(
        self,
        user_id: Optional[str],
        result: str,
        method: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> bool:
        """Log authentication attempts."""
        event_type = AuditEventType.AUTH_SUCCESS if result == "success" else AuditEventType.AUTH_FAILURE
        severity = AuditSeverity.LOW if result == "success" else AuditSeverity.HIGH
        
        return self.audit_logger.log_security_event(
            event_type=event_type,
            user_id=user_id,
            action="authenticate",
            result=result,
            details={
                "method": method,
                "failure_reason": failure_reason
            },
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_access_attempt(
        self,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str],
        action: str,
        result: str,
        team_id: Optional[str] = None,
        required_permissions: Optional[List[str]] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Log access control attempts."""
        event_type = AuditEventType.ACCESS_GRANTED if result == "success" else AuditEventType.ACCESS_DENIED
        severity = AuditSeverity.LOW if result == "success" else AuditSeverity.MEDIUM
        
        return self.audit_logger.log_security_event(
            event_type=event_type,
            user_id=user_id,
            action=f"{action}_{resource_type}",
            result=result,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "team_id": team_id,
                "required_permissions": required_permissions
            },
            severity=severity,
            ip_address=ip_address
        )
    
    def log_permission_change(
        self,
        admin_user_id: str,
        target_user_id: str,
        team_id: Optional[str],
        old_permissions: List[str],
        new_permissions: List[str],
        ip_address: Optional[str] = None
    ) -> bool:
        """Log permission changes."""
        return self.audit_logger.log_security_event(
            event_type=AuditEventType.PERMISSION_CHANGE,
            user_id=admin_user_id,
            action="change_permissions",
            result="success",
            details={
                "target_user_id": target_user_id,
                "team_id": team_id,
                "old_permissions": old_permissions,
                "new_permissions": new_permissions
            },
            severity=AuditSeverity.HIGH,
            ip_address=ip_address
        )


# Global audit logger instance
audit_logger = AuditLogger()
security_audit_logger = SecurityAuditLogger(audit_logger)