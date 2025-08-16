"""
Workload Analytics Engine for DevSync AI.

This module provides comprehensive workload tracking, analysis, and reporting
capabilities for team members and assignment hooks.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

from devsync_ai.database.connection import get_database
# WorkloadAnalysis is defined locally in this module


logger = logging.getLogger(__name__)


class WorkloadStatus(Enum):
    """Workload status levels."""
    UNDERUTILIZED = "underutilized"
    OPTIMAL = "optimal"
    HIGH = "high"
    OVERLOADED = "overloaded"
    CRITICAL = "critical"


class CapacityAlert(Enum):
    """Types of capacity alerts."""
    APPROACHING_LIMIT = "approaching_limit"
    OVER_CAPACITY = "over_capacity"
    SKILL_MISMATCH = "skill_mismatch"
    VELOCITY_DROP = "velocity_drop"
    DEADLINE_RISK = "deadline_risk"


@dataclass
class WorkloadAnalysis:
    """Team member workload analysis (legacy compatibility)."""
    assignee: str
    current_tickets: int
    total_story_points: int
    capacity_utilization: float
    overloaded: bool
    skill_match_score: float
    recent_velocity: float
    estimated_completion_date: Optional[datetime]


@dataclass
class TeamMemberCapacity:
    """Team member capacity and workload information."""
    user_id: str
    display_name: str
    email: str
    team_id: str
    
    # Current workload
    active_tickets: int
    total_story_points: int
    estimated_hours: float
    
    # Capacity metrics
    max_concurrent_tickets: int
    weekly_capacity_hours: float
    capacity_utilization: float
    
    # Performance metrics
    recent_velocity: float  # story points per sprint
    average_completion_time: float  # hours per story point
    quality_score: float  # 0.0 to 1.0
    
    # Status and alerts
    workload_status: WorkloadStatus
    alerts: List[CapacityAlert]
    
    # Predictions
    estimated_completion_date: Optional[datetime]
    projected_capacity_date: Optional[datetime]
    
    # Skills and preferences
    skill_areas: List[str]
    preferred_ticket_types: List[str]
    
    # Metadata
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkloadDistribution:
    """Team workload distribution analysis."""
    team_id: str
    total_active_tickets: int
    total_story_points: int
    total_estimated_hours: float
    
    # Distribution metrics
    workload_variance: float
    utilization_average: float
    utilization_std_dev: float
    
    # Member breakdown
    members: List[TeamMemberCapacity]
    overloaded_members: List[str]
    underutilized_members: List[str]
    
    # Alerts and recommendations
    distribution_alerts: List[str]
    rebalancing_suggestions: List[Dict[str, Any]]
    
    # Trends
    velocity_trend: str  # "increasing", "stable", "decreasing"
    capacity_trend: str
    
    last_updated: datetime


@dataclass
class AssignmentImpactAnalysis:
    """Analysis of assignment impact on team member and team."""
    assignee_id: str
    ticket_key: str
    story_points: int
    estimated_hours: float
    
    # Pre-assignment state
    current_workload: TeamMemberCapacity
    
    # Post-assignment predictions
    projected_utilization: float
    projected_completion_date: datetime
    projected_workload_status: WorkloadStatus
    
    # Impact assessment
    impact_severity: str  # "low", "medium", "high", "critical"
    capacity_warnings: List[str]
    skill_match_score: float
    
    # Recommendations
    assignment_recommendation: str  # "approve", "caution", "reject", "reassign"
    alternative_assignees: List[Tuple[str, float]]  # (user_id, suitability_score)
    
    # Team impact
    team_impact: Dict[str, Any]
    
    created_at: datetime


class WorkloadAnalyticsEngine:
    """
    Comprehensive workload analytics engine for team capacity management.
    
    Provides real-time workload tracking, assignment impact analysis,
    and capacity planning capabilities.
    """
    
    def __init__(self):
        self.db_connection = None
        self._capacity_cache = {}
        self._cache_ttl = timedelta(minutes=5)
        self._last_cache_update = {}
    
    async def initialize(self):
        """Initialize the workload analytics engine."""
        try:
            self.db_connection = await get_database()
            logger.info("Workload analytics engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize workload analytics engine: {e}")
            raise
    
    async def get_team_member_capacity(self, user_id: str, team_id: str) -> Optional[TeamMemberCapacity]:
        """Get current capacity information for a team member."""
        try:
            # Check cache first
            cache_key = f"{user_id}_{team_id}"
            if self._is_cache_valid(cache_key):
                return self._capacity_cache.get(cache_key)
            
            # Query database for current workload
            workload_data = await self._query_member_workload(user_id, team_id)
            if not workload_data:
                return None
            
            # Calculate capacity metrics
            capacity = await self._calculate_member_capacity(workload_data)
            
            # Update cache
            self._capacity_cache[cache_key] = capacity
            self._last_cache_update[cache_key] = datetime.now(timezone.utc)
            
            return capacity
            
        except Exception as e:
            logger.error(f"Failed to get team member capacity for {user_id}: {e}")
            return None
    
    async def analyze_assignment_impact(
        self, 
        assignee_id: str, 
        team_id: str,
        ticket_key: str,
        story_points: int,
        estimated_hours: float,
        ticket_metadata: Dict[str, Any] = None
    ) -> AssignmentImpactAnalysis:
        """Analyze the impact of assigning a ticket to a team member."""
        try:
            # Get current capacity
            current_capacity = await self.get_team_member_capacity(assignee_id, team_id)
            if not current_capacity:
                # Create minimal capacity for unknown members
                current_capacity = await self._create_default_capacity(assignee_id, team_id)
            
            # Calculate projected metrics
            projected_utilization = await self._calculate_projected_utilization(
                current_capacity, story_points, estimated_hours
            )
            
            projected_completion_date = await self._estimate_completion_date(
                current_capacity, story_points, estimated_hours
            )
            
            projected_status = self._determine_workload_status(projected_utilization)
            
            # Assess impact severity
            impact_severity = self._assess_impact_severity(
                current_capacity, projected_utilization, projected_status
            )
            
            # Generate capacity warnings
            warnings = self._generate_capacity_warnings(
                current_capacity, projected_utilization, projected_status
            )
            
            # Calculate skill match
            skill_match_score = await self._calculate_skill_match(
                current_capacity, ticket_metadata or {}
            )
            
            # Generate assignment recommendation
            recommendation = self._generate_assignment_recommendation(
                impact_severity, skill_match_score, projected_status
            )
            
            # Find alternative assignees if needed
            alternatives = []
            if recommendation in ["caution", "reject", "reassign"]:
                alternatives = await self._find_alternative_assignees(
                    team_id, story_points, estimated_hours, ticket_metadata or {}
                )
            
            # Analyze team impact
            team_impact = await self._analyze_team_impact(
                team_id, assignee_id, story_points, estimated_hours
            )
            
            return AssignmentImpactAnalysis(
                assignee_id=assignee_id,
                ticket_key=ticket_key,
                story_points=story_points,
                estimated_hours=estimated_hours,
                current_workload=current_capacity,
                projected_utilization=projected_utilization,
                projected_completion_date=projected_completion_date,
                projected_workload_status=projected_status,
                impact_severity=impact_severity,
                capacity_warnings=warnings,
                skill_match_score=skill_match_score,
                assignment_recommendation=recommendation,
                alternative_assignees=alternatives,
                team_impact=team_impact,
                created_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze assignment impact: {e}")
            raise
    
    async def get_team_workload_distribution(self, team_id: str) -> WorkloadDistribution:
        """Get comprehensive workload distribution for a team."""
        try:
            # Get all team members
            team_members = await self._get_team_members(team_id)
            
            # Get capacity for each member
            member_capacities = []
            for member_id in team_members:
                capacity = await self.get_team_member_capacity(member_id, team_id)
                if capacity:
                    member_capacities.append(capacity)
            
            if not member_capacities:
                return self._create_empty_distribution(team_id)
            
            # Calculate distribution metrics
            total_tickets = sum(m.active_tickets for m in member_capacities)
            total_points = sum(m.total_story_points for m in member_capacities)
            total_hours = sum(m.estimated_hours for m in member_capacities)
            
            utilizations = [m.capacity_utilization for m in member_capacities]
            avg_utilization = statistics.mean(utilizations)
            std_utilization = statistics.stdev(utilizations) if len(utilizations) > 1 else 0.0
            workload_variance = statistics.variance([m.active_tickets for m in member_capacities]) if len(member_capacities) > 1 else 0.0
            
            # Identify overloaded and underutilized members
            overloaded = [m.user_id for m in member_capacities if m.workload_status in [WorkloadStatus.OVERLOADED, WorkloadStatus.CRITICAL]]
            underutilized = [m.user_id for m in member_capacities if m.workload_status == WorkloadStatus.UNDERUTILIZED]
            
            # Generate alerts and suggestions
            alerts = self._generate_distribution_alerts(member_capacities, avg_utilization, std_utilization)
            suggestions = await self._generate_rebalancing_suggestions(member_capacities)
            
            # Calculate trends
            velocity_trend = await self._calculate_velocity_trend(team_id)
            capacity_trend = await self._calculate_capacity_trend(team_id)
            
            return WorkloadDistribution(
                team_id=team_id,
                total_active_tickets=total_tickets,
                total_story_points=total_points,
                total_estimated_hours=total_hours,
                workload_variance=workload_variance,
                utilization_average=avg_utilization,
                utilization_std_dev=std_utilization,
                members=member_capacities,
                overloaded_members=overloaded,
                underutilized_members=underutilized,
                distribution_alerts=alerts,
                rebalancing_suggestions=suggestions,
                velocity_trend=velocity_trend,
                capacity_trend=capacity_trend,
                last_updated=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to get team workload distribution: {e}")
            raise
    
    async def generate_capacity_alerts(self, team_id: str) -> List[Dict[str, Any]]:
        """Generate capacity alerts for a team."""
        try:
            distribution = await self.get_team_workload_distribution(team_id)
            alerts = []
            
            # Check for overloaded members
            for member_id in distribution.overloaded_members:
                member = next((m for m in distribution.members if m.user_id == member_id), None)
                if member:
                    alerts.append({
                        "type": "overload_warning",
                        "severity": "high",
                        "member_id": member_id,
                        "member_name": member.display_name,
                        "utilization": member.capacity_utilization,
                        "active_tickets": member.active_tickets,
                        "message": f"{member.display_name} is overloaded with {member.active_tickets} active tickets ({member.capacity_utilization:.0%} capacity)",
                        "recommendations": [
                            "Consider reassigning some tickets",
                            "Extend deadlines if possible",
                            "Provide additional support"
                        ]
                    })
            
            # Check for high workload variance
            if distribution.workload_variance > 5.0:  # Threshold for high variance
                alerts.append({
                    "type": "uneven_distribution",
                    "severity": "medium",
                    "variance": distribution.workload_variance,
                    "message": f"Uneven workload distribution detected (variance: {distribution.workload_variance:.1f})",
                    "recommendations": distribution.rebalancing_suggestions
                })
            
            # Check for declining velocity
            if distribution.velocity_trend == "decreasing":
                alerts.append({
                    "type": "velocity_decline",
                    "severity": "medium",
                    "trend": distribution.velocity_trend,
                    "message": "Team velocity is declining",
                    "recommendations": [
                        "Review current workload distribution",
                        "Identify and address blockers",
                        "Consider process improvements"
                    ]
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to generate capacity alerts: {e}")
            return []
    
    async def update_member_workload(
        self, 
        user_id: str, 
        team_id: str, 
        ticket_key: str, 
        action: str,  # "assigned", "completed", "removed"
        story_points: int = 0,
        estimated_hours: float = 0.0
    ) -> bool:
        """Update member workload after ticket assignment/completion."""
        try:
            # Invalidate cache
            cache_key = f"{user_id}_{team_id}"
            if cache_key in self._capacity_cache:
                del self._capacity_cache[cache_key]
            
            # Update database
            await self._update_workload_database(
                user_id, team_id, ticket_key, action, story_points, estimated_hours
            )
            
            # Log the update
            logger.info(f"Updated workload for {user_id}: {action} {ticket_key} ({story_points} points)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update member workload: {e}")
            return False
    
    # Private helper methods
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._last_cache_update:
            return False
        
        last_update = self._last_cache_update[cache_key]
        return datetime.now(timezone.utc) - last_update < self._cache_ttl
    
    async def _query_member_workload(self, user_id: str, team_id: str) -> Optional[Dict[str, Any]]:
        """Query database for member workload data."""
        try:
            if not self.db_connection:
                await self.initialize()
            
            # Query active tickets for the user from hook_executions table
            # Note: This is a simplified query since we're using Supabase PostgREST
            # In a real implementation, you might need to use RPC functions for complex queries
            
            # For now, return mock data based on user_id and team_id
            # In production, this would query the actual database
            return {
                "user_id": user_id,
                "team_id": team_id,
                "active_tickets": 4,  # Mock data
                "total_story_points": 20,  # Mock data
                "estimated_hours": 80.0,  # Mock data
                "avg_story_points": 5.0,  # Mock data
                "display_name": f"User {user_id}",
                "email": f"{user_id}@company.com"
            }
            
        except Exception as e:
            logger.error(f"Failed to query member workload: {e}")
            return None
    
    async def _calculate_member_capacity(self, workload_data: Dict[str, Any]) -> TeamMemberCapacity:
        """Calculate comprehensive capacity metrics for a team member."""
        try:
            user_id = workload_data["user_id"]
            team_id = workload_data["team_id"]
            
            # Get configuration-based capacity limits
            max_tickets = await self._get_max_concurrent_tickets(user_id, team_id)
            weekly_hours = await self._get_weekly_capacity_hours(user_id, team_id)
            
            # Calculate utilization
            current_tickets = workload_data["active_tickets"]
            current_points = workload_data["total_story_points"]
            current_hours = workload_data["estimated_hours"]
            
            ticket_utilization = current_tickets / max_tickets if max_tickets > 0 else 0
            hour_utilization = current_hours / weekly_hours if weekly_hours > 0 else 0
            capacity_utilization = max(ticket_utilization, hour_utilization)
            
            # Get performance metrics
            velocity = await self._get_recent_velocity(user_id, team_id)
            completion_time = await self._get_average_completion_time(user_id, team_id)
            quality_score = await self._get_quality_score(user_id, team_id)
            
            # Determine workload status
            workload_status = self._determine_workload_status(capacity_utilization)
            
            # Generate alerts
            alerts = self._generate_member_alerts(capacity_utilization, current_tickets, max_tickets)
            
            # Calculate predictions
            completion_date = await self._estimate_member_completion_date(
                current_points, velocity, completion_time
            )
            capacity_date = await self._estimate_capacity_availability_date(
                capacity_utilization, velocity
            )
            
            # Get skills and preferences
            skills = await self._get_member_skills(user_id, team_id)
            preferences = await self._get_ticket_preferences(user_id, team_id)
            
            return TeamMemberCapacity(
                user_id=user_id,
                display_name=workload_data["display_name"],
                email=workload_data["email"],
                team_id=team_id,
                active_tickets=current_tickets,
                total_story_points=current_points,
                estimated_hours=current_hours,
                max_concurrent_tickets=max_tickets,
                weekly_capacity_hours=weekly_hours,
                capacity_utilization=capacity_utilization,
                recent_velocity=velocity,
                average_completion_time=completion_time,
                quality_score=quality_score,
                workload_status=workload_status,
                alerts=alerts,
                estimated_completion_date=completion_date,
                projected_capacity_date=capacity_date,
                skill_areas=skills,
                preferred_ticket_types=preferences,
                last_updated=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate member capacity: {e}")
            raise
    
    def _determine_workload_status(self, utilization: float) -> WorkloadStatus:
        """Determine workload status based on utilization."""
        if utilization >= 1.2:
            return WorkloadStatus.CRITICAL
        elif utilization >= 1.0:
            return WorkloadStatus.OVERLOADED
        elif utilization >= 0.8:
            return WorkloadStatus.HIGH
        elif utilization >= 0.4:
            return WorkloadStatus.OPTIMAL
        else:
            return WorkloadStatus.UNDERUTILIZED
    
    def _generate_member_alerts(self, utilization: float, current_tickets: int, max_tickets: int) -> List[CapacityAlert]:
        """Generate alerts for a team member."""
        alerts = []
        
        if utilization >= 1.0:
            alerts.append(CapacityAlert.OVER_CAPACITY)
        elif utilization >= 0.9:
            alerts.append(CapacityAlert.APPROACHING_LIMIT)
        
        if current_tickets >= max_tickets:
            alerts.append(CapacityAlert.OVER_CAPACITY)
        
        return alerts
    
    async def _create_default_capacity(self, user_id: str, team_id: str) -> TeamMemberCapacity:
        """Create default capacity for unknown members."""
        return TeamMemberCapacity(
            user_id=user_id,
            display_name=f"User {user_id}",
            email=f"{user_id}@company.com",
            team_id=team_id,
            active_tickets=0,
            total_story_points=0,
            estimated_hours=0.0,
            max_concurrent_tickets=5,
            weekly_capacity_hours=40.0,
            capacity_utilization=0.0,
            recent_velocity=8.0,
            average_completion_time=4.0,
            quality_score=0.8,
            workload_status=WorkloadStatus.OPTIMAL,
            alerts=[],
            estimated_completion_date=None,
            projected_capacity_date=datetime.now(timezone.utc),
            skill_areas=["general"],
            preferred_ticket_types=["story"],
            last_updated=datetime.now(timezone.utc)
        )
    
    # Additional helper methods would be implemented here...
    # (Truncated for brevity, but would include all the async methods referenced above)


    async def _calculate_projected_utilization(
        self, 
        current_capacity: TeamMemberCapacity, 
        additional_points: int, 
        additional_hours: float
    ) -> float:
        """Calculate projected utilization after assignment."""
        new_tickets = current_capacity.active_tickets + 1
        
        # Calculate ticket-based utilization
        ticket_util = new_tickets / current_capacity.max_concurrent_tickets if current_capacity.max_concurrent_tickets > 0 else 0
        
        # For hour-based utilization, we need to consider this as a percentage increase
        # rather than absolute hours vs weekly capacity
        current_hour_util = current_capacity.capacity_utilization
        hour_increase_ratio = additional_hours / (current_capacity.estimated_hours if current_capacity.estimated_hours > 0 else 40.0)
        projected_hour_util = current_hour_util + (current_hour_util * hour_increase_ratio)
        
        # Return the higher of the two utilization measures
        return max(ticket_util, projected_hour_util)
    
    async def _estimate_completion_date(
        self, 
        current_capacity: TeamMemberCapacity, 
        additional_points: int, 
        additional_hours: float
    ) -> datetime:
        """Estimate completion date for current workload plus new assignment."""
        total_points = current_capacity.total_story_points + additional_points
        velocity = current_capacity.recent_velocity
        
        if velocity > 0:
            weeks_to_complete = total_points / velocity
            return datetime.now(timezone.utc) + timedelta(weeks=weeks_to_complete)
        else:
            # Fallback to hours-based estimation
            total_hours = current_capacity.estimated_hours + additional_hours
            hours_per_week = current_capacity.weekly_capacity_hours
            weeks_to_complete = total_hours / hours_per_week if hours_per_week > 0 else 1
            return datetime.now(timezone.utc) + timedelta(weeks=weeks_to_complete)
    
    def _assess_impact_severity(
        self, 
        current_capacity: TeamMemberCapacity, 
        projected_utilization: float, 
        projected_status: WorkloadStatus
    ) -> str:
        """Assess the severity of assignment impact."""
        if projected_status == WorkloadStatus.CRITICAL:
            return "critical"
        elif projected_status == WorkloadStatus.OVERLOADED:
            return "high"
        elif projected_utilization > 0.9:
            return "medium"
        else:
            return "low"
    
    def _generate_capacity_warnings(
        self, 
        current_capacity: TeamMemberCapacity, 
        projected_utilization: float, 
        projected_status: WorkloadStatus
    ) -> List[str]:
        """Generate capacity warnings for assignment."""
        warnings = []
        
        if projected_status == WorkloadStatus.CRITICAL:
            warnings.append("Assignment will put member in critical overload state")
        elif projected_status == WorkloadStatus.OVERLOADED:
            warnings.append("Assignment will overload member beyond capacity")
        elif projected_utilization > 0.9:
            warnings.append("Assignment will bring member close to capacity limit")
        
        if current_capacity.active_tickets >= current_capacity.max_concurrent_tickets:
            warnings.append("Member already at maximum concurrent ticket limit")
        
        return warnings
    
    async def _calculate_skill_match(
        self, 
        capacity: TeamMemberCapacity, 
        ticket_metadata: Dict[str, Any]
    ) -> float:
        """Calculate skill match score between member and ticket."""
        try:
            # Extract ticket requirements
            ticket_skills = ticket_metadata.get("required_skills", [])
            ticket_type = ticket_metadata.get("ticket_type", "")
            ticket_components = ticket_metadata.get("components", [])
            
            if not ticket_skills and not ticket_type and not ticket_components:
                return 0.7  # Default moderate match
            
            # Calculate match score
            skill_matches = 0
            total_skills = len(ticket_skills) if ticket_skills else 1
            
            for skill in ticket_skills:
                if skill.lower() in [s.lower() for s in capacity.skill_areas]:
                    skill_matches += 1
            
            # Check ticket type preference
            type_match = 0
            if ticket_type.lower() in [t.lower() for t in capacity.preferred_ticket_types]:
                type_match = 0.3
            
            # Base skill match score
            skill_score = skill_matches / total_skills if total_skills > 0 else 0.5
            
            # Combined score
            return min(1.0, skill_score + type_match)
            
        except Exception as e:
            logger.warning(f"Failed to calculate skill match: {e}")
            return 0.5  # Default moderate match
    
    def _generate_assignment_recommendation(
        self, 
        impact_severity: str, 
        skill_match_score: float, 
        projected_status: WorkloadStatus
    ) -> str:
        """Generate assignment recommendation."""
        if projected_status == WorkloadStatus.CRITICAL:
            return "reject"
        elif projected_status == WorkloadStatus.OVERLOADED:
            return "reassign"
        elif impact_severity == "high" and skill_match_score < 0.5:
            return "caution"
        elif skill_match_score >= 0.8 and impact_severity in ["low", "medium"]:
            return "approve"
        else:
            return "caution"
    
    async def _find_alternative_assignees(
        self, 
        team_id: str, 
        story_points: int, 
        estimated_hours: float, 
        ticket_metadata: Dict[str, Any]
    ) -> List[Tuple[str, float]]:
        """Find alternative assignees with suitability scores."""
        try:
            team_members = await self._get_team_members(team_id)
            alternatives = []
            
            for member_id in team_members:
                capacity = await self.get_team_member_capacity(member_id, team_id)
                if not capacity:
                    continue
                
                # Calculate suitability score
                projected_util = await self._calculate_projected_utilization(
                    capacity, story_points, estimated_hours
                )
                skill_match = await self._calculate_skill_match(capacity, ticket_metadata)
                
                # Suitability factors
                capacity_factor = max(0, 1.0 - projected_util)  # Lower utilization is better
                skill_factor = skill_match
                velocity_factor = min(1.0, capacity.recent_velocity / 10.0)  # Normalize velocity
                
                suitability = (capacity_factor * 0.4 + skill_factor * 0.4 + velocity_factor * 0.2)
                
                if suitability > 0.3:  # Minimum threshold
                    alternatives.append((member_id, suitability))
            
            # Sort by suitability score
            alternatives.sort(key=lambda x: x[1], reverse=True)
            return alternatives[:5]  # Top 5 alternatives
            
        except Exception as e:
            logger.error(f"Failed to find alternative assignees: {e}")
            return []
    
    async def _analyze_team_impact(
        self, 
        team_id: str, 
        assignee_id: str, 
        story_points: int, 
        estimated_hours: float
    ) -> Dict[str, Any]:
        """Analyze impact of assignment on team dynamics."""
        try:
            distribution = await self.get_team_workload_distribution(team_id)
            
            # Find assignee in distribution
            assignee = next((m for m in distribution.members if m.user_id == assignee_id), None)
            if not assignee:
                return {"impact": "unknown", "reason": "assignee not found in team"}
            
            # Calculate new team metrics
            new_total_points = distribution.total_story_points + story_points
            new_assignee_points = assignee.total_story_points + story_points
            
            # Check if this creates imbalance
            avg_points_per_member = new_total_points / len(distribution.members)
            assignee_deviation = abs(new_assignee_points - avg_points_per_member)
            
            impact_level = "low"
            reasons = []
            
            if assignee_deviation > avg_points_per_member * 0.5:
                impact_level = "high"
                reasons.append("Creates significant workload imbalance")
            
            if len(distribution.overloaded_members) > len(distribution.members) * 0.3:
                impact_level = "medium"
                reasons.append("Team already has multiple overloaded members")
            
            return {
                "impact": impact_level,
                "reasons": reasons,
                "team_utilization": distribution.utilization_average,
                "workload_variance": distribution.workload_variance,
                "overloaded_count": len(distribution.overloaded_members)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze team impact: {e}")
            return {"impact": "unknown", "error": str(e)}
    
    async def _get_team_members(self, team_id: str) -> List[str]:
        """Get list of team member IDs."""
        try:
            if not self.db_connection:
                await self.initialize()
            
            # For now, return mock team members
            # In production, this would query the actual database
            return [f"user{i}" for i in range(1, 6)]  # Mock team of 5 members
            
        except Exception as e:
            logger.error(f"Failed to get team members: {e}")
            return []
    
    def _create_empty_distribution(self, team_id: str) -> WorkloadDistribution:
        """Create empty workload distribution."""
        return WorkloadDistribution(
            team_id=team_id,
            total_active_tickets=0,
            total_story_points=0,
            total_estimated_hours=0.0,
            workload_variance=0.0,
            utilization_average=0.0,
            utilization_std_dev=0.0,
            members=[],
            overloaded_members=[],
            underutilized_members=[],
            distribution_alerts=[],
            rebalancing_suggestions=[],
            velocity_trend="stable",
            capacity_trend="stable",
            last_updated=datetime.now(timezone.utc)
        )
    
    def _generate_distribution_alerts(
        self, 
        members: List[TeamMemberCapacity], 
        avg_utilization: float, 
        std_utilization: float
    ) -> List[str]:
        """Generate distribution alerts."""
        alerts = []
        
        if avg_utilization > 0.9:
            alerts.append("Team average utilization is very high")
        
        if std_utilization > 0.3:
            alerts.append("High variance in workload distribution")
        
        overloaded_count = sum(1 for m in members if m.workload_status in [WorkloadStatus.OVERLOADED, WorkloadStatus.CRITICAL])
        if overloaded_count > len(members) * 0.3:
            alerts.append(f"{overloaded_count} team members are overloaded")
        
        return alerts
    
    async def _generate_rebalancing_suggestions(
        self, 
        members: List[TeamMemberCapacity]
    ) -> List[Dict[str, Any]]:
        """Generate workload rebalancing suggestions."""
        suggestions = []
        
        # Find overloaded and underutilized members
        overloaded = [m for m in members if m.workload_status in [WorkloadStatus.OVERLOADED, WorkloadStatus.CRITICAL]]
        underutilized = [m for m in members if m.workload_status == WorkloadStatus.UNDERUTILIZED]
        
        for overloaded_member in overloaded:
            for underutilized_member in underutilized:
                # Calculate potential transfer
                excess_tickets = overloaded_member.active_tickets - overloaded_member.max_concurrent_tickets
                available_capacity = underutilized_member.max_concurrent_tickets - underutilized_member.active_tickets
                
                if excess_tickets > 0 and available_capacity > 0:
                    transfer_count = min(excess_tickets, available_capacity, 2)  # Max 2 tickets per suggestion
                    
                    suggestions.append({
                        "type": "reassign_tickets",
                        "from_member": overloaded_member.user_id,
                        "to_member": underutilized_member.user_id,
                        "ticket_count": transfer_count,
                        "reason": f"Rebalance workload between {overloaded_member.display_name} and {underutilized_member.display_name}"
                    })
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    async def _calculate_velocity_trend(self, team_id: str) -> str:
        """Calculate team velocity trend."""
        try:
            # This would typically analyze historical velocity data
            # For now, return a placeholder
            return "stable"
        except Exception:
            return "stable"
    
    async def _calculate_capacity_trend(self, team_id: str) -> str:
        """Calculate team capacity trend."""
        try:
            # This would typically analyze historical capacity data
            # For now, return a placeholder
            return "stable"
        except Exception:
            return "stable"
    
    async def _update_workload_database(
        self, 
        user_id: str, 
        team_id: str, 
        ticket_key: str, 
        action: str, 
        story_points: int, 
        estimated_hours: float
    ) -> None:
        """Update workload information in database."""
        try:
            if not self.db_connection:
                await self.initialize()
            
            # Insert workload update record using Supabase client
            data = {
                "hook_id": "workload_update",
                "hook_type": "workload_tracking",
                "event_id": f"workload_{user_id}_{ticket_key}",
                "team_id": team_id,
                "ticket_key": ticket_key,
                "success": True,
                "execution_time_ms": 0,
                "metadata": {
                    "assignee_id": user_id,
                    "action": action,
                    "story_points": story_points,
                    "estimated_hours": estimated_hours,
                    "workload_update": True
                }
            }
            
            await self.db_connection.insert("hook_executions", data)
            
        except Exception as e:
            logger.error(f"Failed to update workload database: {e}")
            raise
    
    # Configuration and metrics helper methods
    
    async def _get_max_concurrent_tickets(self, user_id: str, team_id: str) -> int:
        """Get maximum concurrent tickets for a user."""
        # This would typically come from team configuration
        return 5  # Default value
    
    async def _get_weekly_capacity_hours(self, user_id: str, team_id: str) -> float:
        """Get weekly capacity hours for a user."""
        # This would typically come from team configuration
        return 40.0  # Default value
    
    async def _get_recent_velocity(self, user_id: str, team_id: str) -> float:
        """Get recent velocity for a user."""
        # This would calculate from historical data
        return 8.0  # Default value
    
    async def _get_average_completion_time(self, user_id: str, team_id: str) -> float:
        """Get average completion time per story point."""
        # This would calculate from historical data
        return 4.0  # Default value
    
    async def _get_quality_score(self, user_id: str, team_id: str) -> float:
        """Get quality score for a user."""
        # This would calculate from bug rates, rework, etc.
        return 0.8  # Default value
    
    async def _estimate_member_completion_date(
        self, 
        story_points: int, 
        velocity: float, 
        completion_time: float
    ) -> Optional[datetime]:
        """Estimate when member will complete current workload."""
        if velocity > 0:
            weeks = story_points / velocity
            return datetime.now(timezone.utc) + timedelta(weeks=weeks)
        return None
    
    async def _estimate_capacity_availability_date(
        self, 
        utilization: float, 
        velocity: float
    ) -> Optional[datetime]:
        """Estimate when member will have capacity available."""
        if utilization <= 0.8:
            return datetime.now(timezone.utc)  # Already has capacity
        
        # Estimate based on velocity
        if velocity > 0:
            weeks_to_capacity = (utilization - 0.8) * 10  # Rough estimation
            return datetime.now(timezone.utc) + timedelta(weeks=weeks_to_capacity)
        
        return None
    
    async def _get_member_skills(self, user_id: str, team_id: str) -> List[str]:
        """Get skill areas for a team member."""
        # This would typically come from user profile or team configuration
        return ["general", "backend", "frontend"]  # Default skills
    
    async def _get_ticket_preferences(self, user_id: str, team_id: str) -> List[str]:
        """Get ticket type preferences for a team member."""
        # This would typically come from user profile or historical data
        return ["story", "task", "bug"]  # Default preferences


# Global instance
default_workload_analytics_engine = WorkloadAnalyticsEngine()