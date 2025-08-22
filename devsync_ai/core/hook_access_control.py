"""
Hook Access Control Module

Provides team-based access control for hook configurations and operations.
Implements role-based permissions and team isolation for security.
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Available permissions for hook operations."""
    READ_HOOKS = "read_hooks"
    WRITE_HOOKS = "write_hooks"
    DELETE_HOOKS = "delete_hooks"
    MANAGE_TEAM = "manage_team"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_SECURITY = "manage_security"
    EXECUTE_HOOKS = "execute_hooks"
    CONFIGURE_RULES = "configure_rules"


class Role(Enum):
    """Available roles with different permission sets."""
    VIEWER = "viewer"
    DEVELOPER = "developer"
    TEAM_LEAD = "team_lead"
    ADMIN = "admin"
    SYSTEM_ADMIN = "system_admin"


@dataclass
class User:
    """User information for access control."""
    user_id: str
    username: str
    email: str
    teams: List[str]
    global_roles: List[Role]
    team_roles: Dict[str, List[Role]]
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


@dataclass
class Team:
    """Team information for access control."""
    team_id: str
    name: str
    description: str
    members: List[str]
    admins: List[str]
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class AccessRequest:
    """Request for access validation."""
    user_id: str
    team_id: Optional[str]
    resource_type: str  # "hook", "configuration", "analytics", etc.
    resource_id: Optional[str]
    action: str  # "read", "write", "delete", "execute"
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass
class AccessResult:
    """Result of access control check."""
    granted: bool
    reason: str
    required_permissions: List[Permission]
    user_permissions: List[Permission]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RolePermissionManager:
    """Manages role-to-permission mappings."""
    
    ROLE_PERMISSIONS = {
        Role.VIEWER: [
            Permission.READ_HOOKS,
            Permission.VIEW_ANALYTICS
        ],
        Role.DEVELOPER: [
            Permission.READ_HOOKS,
            Permission.WRITE_HOOKS,
            Permission.EXECUTE_HOOKS,
            Permission.VIEW_ANALYTICS
        ],
        Role.TEAM_LEAD: [
            Permission.READ_HOOKS,
            Permission.WRITE_HOOKS,
            Permission.DELETE_HOOKS,
            Permission.EXECUTE_HOOKS,
            Permission.CONFIGURE_RULES,
            Permission.VIEW_ANALYTICS,
            Permission.MANAGE_TEAM
        ],
        Role.ADMIN: [
            Permission.READ_HOOKS,
            Permission.WRITE_HOOKS,
            Permission.DELETE_HOOKS,
            Permission.EXECUTE_HOOKS,
            Permission.CONFIGURE_RULES,
            Permission.VIEW_ANALYTICS,
            Permission.MANAGE_TEAM,
            Permission.MANAGE_SECURITY
        ],
        Role.SYSTEM_ADMIN: list(Permission)  # All permissions
    }
    
    @classmethod
    def get_permissions_for_role(cls, role: Role) -> Set[Permission]:
        """Get all permissions for a given role."""
        return set(cls.ROLE_PERMISSIONS.get(role, []))
    
    @classmethod
    def get_permissions_for_roles(cls, roles: List[Role]) -> Set[Permission]:
        """Get combined permissions for multiple roles."""
        permissions = set()
        for role in roles:
            permissions.update(cls.get_permissions_for_role(role))
        return permissions


class TeamAccessController:
    """Controls access to team-specific resources."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.teams: Dict[str, Team] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def add_user(self, user: User) -> bool:
        """Add a user to the access control system."""
        try:
            self.users[user.user_id] = user
            self.logger.info(f"Added user {user.username} ({user.user_id})")
            return True
        except Exception as e:
            self.logger.error(f"Error adding user {user.user_id}: {e}")
            return False
    
    def add_team(self, team: Team) -> bool:
        """Add a team to the access control system."""
        try:
            self.teams[team.team_id] = team
            self.logger.info(f"Added team {team.name} ({team.team_id})")
            return True
        except Exception as e:
            self.logger.error(f"Error adding team {team.team_id}: {e}")
            return False
    
    def get_user_permissions(self, user_id: str, team_id: Optional[str] = None) -> Set[Permission]:
        """Get all permissions for a user, optionally within a specific team."""
        try:
            user = self.users.get(user_id)
            if not user or not user.is_active:
                return set()
            
            permissions = set()
            
            # Add global role permissions
            permissions.update(
                RolePermissionManager.get_permissions_for_roles(user.global_roles)
            )
            
            # Add team-specific role permissions
            if team_id and team_id in user.team_roles:
                team_roles = user.team_roles[team_id]
                permissions.update(
                    RolePermissionManager.get_permissions_for_roles(team_roles)
                )
            
            return permissions
            
        except Exception as e:
            self.logger.error(f"Error getting permissions for user {user_id}: {e}")
            return set()
    
    def check_team_membership(self, user_id: str, team_id: str) -> bool:
        """Check if user is a member of the specified team."""
        try:
            user = self.users.get(user_id)
            team = self.teams.get(team_id)
            
            if not user or not team or not user.is_active or not team.is_active:
                return False
            
            return team_id in user.teams or user_id in team.members
            
        except Exception as e:
            self.logger.error(f"Error checking team membership: {e}")
            return False
    
    def check_team_admin(self, user_id: str, team_id: str) -> bool:
        """Check if user is an admin of the specified team."""
        try:
            team = self.teams.get(team_id)
            if not team or not team.is_active:
                return False
            
            return user_id in team.admins
            
        except Exception as e:
            self.logger.error(f"Error checking team admin status: {e}")
            return False
    
    def validate_access(self, request: AccessRequest) -> AccessResult:
        """Validate access request against permissions and team membership."""
        try:
            user = self.users.get(request.user_id)
            if not user or not user.is_active:
                return AccessResult(
                    granted=False,
                    reason="User not found or inactive",
                    required_permissions=[],
                    user_permissions=[]
                )
            
            # Check team membership if team-specific resource
            if request.team_id:
                if not self.check_team_membership(request.user_id, request.team_id):
                    return AccessResult(
                        granted=False,
                        reason=f"User not member of team {request.team_id}",
                        required_permissions=[],
                        user_permissions=[]
                    )
            
            # Determine required permissions based on action and resource
            required_permissions = self._get_required_permissions(
                request.resource_type, 
                request.action
            )
            
            # Get user's actual permissions
            user_permissions = self.get_user_permissions(request.user_id, request.team_id)
            
            # Check if user has all required permissions
            missing_permissions = required_permissions - user_permissions
            
            if missing_permissions:
                return AccessResult(
                    granted=False,
                    reason=f"Missing permissions: {[p.value for p in missing_permissions]}",
                    required_permissions=list(required_permissions),
                    user_permissions=list(user_permissions)
                )
            
            return AccessResult(
                granted=True,
                reason="Access granted",
                required_permissions=list(required_permissions),
                user_permissions=list(user_permissions),
                metadata={
                    "team_id": request.team_id,
                    "resource_type": request.resource_type,
                    "action": request.action
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error validating access: {e}")
            return AccessResult(
                granted=False,
                reason=f"Access validation error: {str(e)}",
                required_permissions=[],
                user_permissions=[]
            )
    
    def _get_required_permissions(self, resource_type: str, action: str) -> Set[Permission]:
        """Determine required permissions for a resource type and action."""
        permission_map = {
            ("hook", "read"): {Permission.READ_HOOKS},
            ("hook", "write"): {Permission.WRITE_HOOKS},
            ("hook", "delete"): {Permission.DELETE_HOOKS},
            ("hook", "execute"): {Permission.EXECUTE_HOOKS},
            ("configuration", "read"): {Permission.READ_HOOKS},
            ("configuration", "write"): {Permission.CONFIGURE_RULES},
            ("configuration", "delete"): {Permission.CONFIGURE_RULES},
            ("analytics", "read"): {Permission.VIEW_ANALYTICS},
            ("team", "manage"): {Permission.MANAGE_TEAM},
            ("security", "manage"): {Permission.MANAGE_SECURITY}
        }
        
        return permission_map.get((resource_type, action), set())


class HookAccessControlManager:
    """Main access control manager for hook system."""
    
    def __init__(self):
        self.team_controller = TeamAccessController()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def initialize_default_users_and_teams(self):
        """Initialize default users and teams for development/testing."""
        try:
            # Create default admin user
            admin_user = User(
                user_id="admin",
                username="admin",
                email="admin@example.com",
                teams=["default"],
                global_roles=[Role.SYSTEM_ADMIN],
                team_roles={"default": [Role.ADMIN]},
                created_at=datetime.now()
            )
            self.team_controller.add_user(admin_user)
            
            # Create default team
            default_team = Team(
                team_id="default",
                name="Default Team",
                description="Default team for hook configurations",
                members=["admin"],
                admins=["admin"],
                created_at=datetime.now()
            )
            self.team_controller.add_team(default_team)
            
            self.logger.info("Initialized default users and teams")
            
        except Exception as e:
            self.logger.error(f"Error initializing default users and teams: {e}")
    
    def check_hook_access(
        self, 
        user_id: str, 
        team_id: str, 
        action: str, 
        hook_id: Optional[str] = None
    ) -> AccessResult:
        """Check access for hook operations."""
        request = AccessRequest(
            user_id=user_id,
            team_id=team_id,
            resource_type="hook",
            resource_id=hook_id,
            action=action
        )
        return self.team_controller.validate_access(request)
    
    def check_configuration_access(
        self, 
        user_id: str, 
        team_id: str, 
        action: str
    ) -> AccessResult:
        """Check access for configuration operations."""
        request = AccessRequest(
            user_id=user_id,
            team_id=team_id,
            resource_type="configuration",
            resource_id=None,
            action=action
        )
        return self.team_controller.validate_access(request)
    
    def check_analytics_access(
        self, 
        user_id: str, 
        team_id: Optional[str] = None
    ) -> AccessResult:
        """Check access for analytics operations."""
        request = AccessRequest(
            user_id=user_id,
            team_id=team_id,
            resource_type="analytics",
            resource_id=None,
            action="read"
        )
        return self.team_controller.validate_access(request)
    
    def get_accessible_teams(self, user_id: str) -> List[str]:
        """Get list of teams the user has access to."""
        try:
            user = self.team_controller.users.get(user_id)
            if not user or not user.is_active:
                return []
            
            return user.teams
            
        except Exception as e:
            self.logger.error(f"Error getting accessible teams for user {user_id}: {e}")
            return []


# Global access control manager instance
access_control_manager = HookAccessControlManager()