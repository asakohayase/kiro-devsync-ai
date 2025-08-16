"""
Hook Configuration API Routes.

This module provides REST API endpoints for managing hook configurations,
team rules, and validation services.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from devsync_ai.core.hook_configuration_manager import (
    HookConfigurationManager,
    TeamConfiguration,
    HookSettings,
    ValidationResult,
    ConfigurationUpdateResult
)
from devsync_ai.core.hook_configuration_validator import HookConfigurationValidator
from devsync_ai.core.exceptions import ConfigurationError, ValidationError


logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/hook-config", tags=["Hook Configuration"])

# Global instances
_config_manager: Optional[HookConfigurationManager] = None
_validator: Optional[HookConfigurationValidator] = None


def get_config_manager() -> HookConfigurationManager:
    """Get or create configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = HookConfigurationManager()
    return _config_manager


def get_validator() -> HookConfigurationValidator:
    """Get or create validator instance."""
    global _validator
    if _validator is None:
        _validator = HookConfigurationValidator()
    return _validator


# Pydantic models for API
class TeamConfigurationResponse(BaseModel):
    """Response model for team configuration."""
    team_id: str
    team_name: str
    enabled: bool
    version: str
    default_channels: Dict[str, str]
    notification_preferences: Dict[str, Any]
    business_hours: Dict[str, Any]
    escalation_rules: List[Dict[str, Any]]
    rules: List[Dict[str, Any]]
    last_updated: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HookSettingsResponse(BaseModel):
    """Response model for hook settings."""
    hook_type: str
    enabled: bool
    execution_conditions: List[Dict[str, Any]]
    notification_channels: List[str]
    rate_limits: Dict[str, Any]
    retry_policy: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResponse(BaseModel):
    """Response model for validation results."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ConfigurationUpdateRequest(BaseModel):
    """Request model for configuration updates."""
    team_name: Optional[str] = None
    enabled: Optional[bool] = None
    default_channels: Optional[Dict[str, str]] = None
    notification_preferences: Optional[Dict[str, Any]] = None
    business_hours: Optional[Dict[str, Any]] = None
    escalation_rules: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class RulesUpdateRequest(BaseModel):
    """Request model for rules updates."""
    rules: List[Dict[str, Any]]


class ConfigurationUpdateResponse(BaseModel):
    """Response model for configuration updates."""
    success: bool
    team_id: str
    updated_fields: List[str] = Field(default_factory=list)
    validation_result: Optional[ValidationResponse] = None
    error_message: Optional[str] = None


# API Endpoints

@router.get("/teams", response_model=List[str])
async def list_teams(
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Get list of all configured teams.
    
    Returns:
        List of team IDs
    """
    try:
        configurations = await config_manager.get_all_team_configurations()
        return [config.team_id for config in configurations]
    except Exception as e:
        logger.error(f"Failed to list teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team list")


@router.get("/teams/{team_id}", response_model=TeamConfigurationResponse)
async def get_team_configuration(
    team_id: str,
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Get configuration for a specific team.
    
    Args:
        team_id: Team identifier
        
    Returns:
        Team configuration
    """
    try:
        config = await config_manager.load_team_configuration(team_id)
        
        return TeamConfigurationResponse(
            team_id=config.team_id,
            team_name=config.team_name,
            enabled=config.enabled,
            version=config.version,
            default_channels=config.default_channels,
            notification_preferences=config.notification_preferences,
            business_hours=config.business_hours,
            escalation_rules=config.escalation_rules,
            rules=config.rules,
            last_updated=config.last_updated,
            metadata=config.metadata
        )
    except ConfigurationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get team configuration for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve team configuration")


@router.put("/teams/{team_id}", response_model=ConfigurationUpdateResponse)
async def update_team_configuration(
    team_id: str,
    updates: ConfigurationUpdateRequest,
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Update team configuration.
    
    Args:
        team_id: Team identifier
        updates: Configuration updates
        
    Returns:
        Update result
    """
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        result = await config_manager.update_team_configuration(team_id, update_dict)
        
        validation_response = None
        if result.validation_result:
            validation_response = ValidationResponse(
                valid=result.validation_result.valid,
                errors=result.validation_result.errors,
                warnings=result.validation_result.warnings,
                suggestions=result.validation_result.suggestions
            )
        
        return ConfigurationUpdateResponse(
            success=result.success,
            team_id=result.team_id,
            updated_fields=result.updated_fields,
            validation_result=validation_response,
            error_message=result.error_message
        )
    except Exception as e:
        logger.error(f"Failed to update team configuration for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update team configuration")


@router.put("/teams/{team_id}/rules", response_model=ConfigurationUpdateResponse)
async def update_team_rules(
    team_id: str,
    request: RulesUpdateRequest,
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Update team rules.
    
    Args:
        team_id: Team identifier
        request: Rules update request
        
    Returns:
        Update result
    """
    try:
        result = await config_manager.update_team_rules(team_id, request.rules)
        
        validation_response = None
        if result.validation_result:
            validation_response = ValidationResponse(
                valid=result.validation_result.valid,
                errors=result.validation_result.errors,
                warnings=result.validation_result.warnings,
                suggestions=result.validation_result.suggestions
            )
        
        return ConfigurationUpdateResponse(
            success=result.success,
            team_id=result.team_id,
            updated_fields=result.updated_fields,
            validation_result=validation_response,
            error_message=result.error_message
        )
    except Exception as e:
        logger.error(f"Failed to update team rules for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update team rules")


@router.get("/teams/{team_id}/hooks/{hook_type}", response_model=HookSettingsResponse)
async def get_hook_settings(
    team_id: str,
    hook_type: str,
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Get hook-specific settings for a team.
    
    Args:
        team_id: Team identifier
        hook_type: Hook type (e.g., 'StatusChangeHook')
        
    Returns:
        Hook settings
    """
    try:
        settings = await config_manager.get_hook_settings(hook_type, team_id)
        
        return HookSettingsResponse(
            hook_type=settings.hook_type,
            enabled=settings.enabled,
            execution_conditions=settings.execution_conditions,
            notification_channels=settings.notification_channels,
            rate_limits=settings.rate_limits,
            retry_policy=settings.retry_policy,
            metadata=settings.metadata
        )
    except Exception as e:
        logger.error(f"Failed to get hook settings for {team_id}/{hook_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hook settings")


@router.post("/teams/{team_id}/validate", response_model=ValidationResponse)
async def validate_team_configuration(
    team_id: str,
    config_data: Dict[str, Any] = Body(...),
    validator: HookConfigurationValidator = Depends(get_validator)
):
    """
    Validate team configuration.
    
    Args:
        team_id: Team identifier
        config_data: Configuration data to validate
        
    Returns:
        Validation result
    """
    try:
        # Ensure team_id is set in config data
        config_data['team_id'] = team_id
        
        result = await validator.validate_team_configuration_schema(config_data)
        
        return ValidationResponse(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings,
            suggestions=result.suggestions
        )
    except Exception as e:
        logger.error(f"Failed to validate team configuration for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate configuration")


@router.post("/validate/rules", response_model=ValidationResponse)
async def validate_rules(
    rules: List[Dict[str, Any]] = Body(...),
    validator: HookConfigurationValidator = Depends(get_validator)
):
    """
    Validate hook rules.
    
    Args:
        rules: List of rules to validate
        
    Returns:
        Validation result
    """
    try:
        result = await validator.validate_hook_rules(rules)
        
        return ValidationResponse(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings,
            suggestions=result.suggestions
        )
    except Exception as e:
        logger.error(f"Failed to validate rules: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate rules")


@router.delete("/teams/{team_id}")
async def delete_team_configuration(
    team_id: str,
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Delete team configuration.
    
    Args:
        team_id: Team identifier
        
    Returns:
        Success status
    """
    try:
        success = await config_manager.delete_team_configuration(team_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Team configuration not found")
        
        return {"success": True, "message": f"Configuration for team '{team_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete team configuration for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete team configuration")


@router.get("/teams/{team_id}/export")
async def export_team_configuration(
    team_id: str,
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Export team configuration as JSON.
    
    Args:
        team_id: Team identifier
        
    Returns:
        Configuration data
    """
    try:
        config_data = await config_manager.export_team_configuration(team_id)
        
        if not config_data:
            raise HTTPException(status_code=404, detail="Team configuration not found")
        
        return config_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export team configuration for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export team configuration")


@router.post("/teams/{team_id}/import", response_model=ConfigurationUpdateResponse)
async def import_team_configuration(
    team_id: str,
    config_data: Dict[str, Any] = Body(...),
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Import team configuration from JSON.
    
    Args:
        team_id: Team identifier
        config_data: Configuration data to import
        
    Returns:
        Import result
    """
    try:
        result = await config_manager.import_team_configuration(team_id, config_data)
        
        validation_response = None
        if result.validation_result:
            validation_response = ValidationResponse(
                valid=result.validation_result.valid,
                errors=result.validation_result.errors,
                warnings=result.validation_result.warnings,
                suggestions=result.validation_result.suggestions
            )
        
        return ConfigurationUpdateResponse(
            success=result.success,
            team_id=result.team_id,
            updated_fields=result.updated_fields,
            validation_result=validation_response,
            error_message=result.error_message
        )
    except Exception as e:
        logger.error(f"Failed to import team configuration for {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to import team configuration")


@router.get("/validation/help")
async def get_validation_help(
    validator: HookConfigurationValidator = Depends(get_validator)
):
    """
    Get validation help information including available fields, operators, and examples.
    
    Returns:
        Validation help data
    """
    try:
        return validator.get_validation_help()
    except Exception as e:
        logger.error(f"Failed to get validation help: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve validation help")


@router.get("/validation/fields")
async def get_field_suggestions(
    partial: str = Query(..., description="Partial field name for suggestions"),
    validator: HookConfigurationValidator = Depends(get_validator)
):
    """
    Get field suggestions based on partial input.
    
    Args:
        partial: Partial field name
        
    Returns:
        List of matching field names
    """
    try:
        suggestions = validator.get_field_suggestions(partial)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Failed to get field suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get field suggestions")


@router.get("/validation/operators")
async def get_operator_suggestions(
    field: str = Query(..., description="Field name to get valid operators for"),
    validator: HookConfigurationValidator = Depends(get_validator)
):
    """
    Get valid operators for a specific field.
    
    Args:
        field: Field name
        
    Returns:
        List of valid operators
    """
    try:
        operators = validator.get_operator_suggestions(field)
        return {"operators": operators}
    except Exception as e:
        logger.error(f"Failed to get operator suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get operator suggestions")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for configuration service.
    
    Returns:
        Service health status
    """
    try:
        # Test database connectivity
        config_manager = get_config_manager()
        await config_manager.get_all_team_configurations()
        
        return {
            "status": "healthy",
            "service": "hook-configuration",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "hook-configuration",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@router.get("/stats")
async def get_configuration_stats(
    config_manager: HookConfigurationManager = Depends(get_config_manager)
):
    """
    Get configuration statistics.
    
    Returns:
        Configuration statistics
    """
    try:
        configurations = await config_manager.get_all_team_configurations()
        
        total_teams = len(configurations)
        enabled_teams = len([c for c in configurations if c.enabled])
        total_rules = sum(len(c.rules) for c in configurations)
        enabled_rules = sum(len([r for r in c.rules if r.get('enabled', True)]) for c in configurations)
        
        # Count hook types
        hook_type_counts = {}
        for config in configurations:
            for rule in config.rules:
                if rule.get('enabled', True):
                    for hook_type in rule.get('hook_types', []):
                        hook_type_counts[hook_type] = hook_type_counts.get(hook_type, 0) + 1
        
        return {
            "total_teams": total_teams,
            "enabled_teams": enabled_teams,
            "disabled_teams": total_teams - enabled_teams,
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "avg_rules_per_team": total_rules / total_teams if total_teams > 0 else 0,
            "hook_type_distribution": hook_type_counts,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get configuration stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration statistics")