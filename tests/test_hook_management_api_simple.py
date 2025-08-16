"""
Simple integration tests for Hook Management API endpoints.

This module provides basic tests to verify the API structure and routing
without complex dependency mocking.
"""

import pytest
import os
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Set required environment variables for testing
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("JIRA_SERVER_URL", "https://test.atlassian.net")
os.environ.setdefault("JIRA_USERNAME", "test@example.com")
os.environ.setdefault("JIRA_API_TOKEN", "test-token")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token")
os.environ.setdefault("GITHUB_TOKEN", "ghp_test-token")

from devsync_ai.api.hook_management_routes import router


@pytest.fixture
def app():
    """Create FastAPI app with hook management routes."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestAPIStructure:
    """Test API structure and routing."""
    
    def test_hook_status_endpoint_exists(self, client):
        """Test that hook status endpoint exists and returns proper error for missing dependencies."""
        response = client.get("/api/v1/hooks/status")
        # Should return 500 due to missing dependencies, but endpoint should exist
        assert response.status_code in [500, 503]
    
    def test_hook_health_endpoint_exists(self, client):
        """Test that hook health endpoint exists."""
        response = client.get("/api/v1/hooks/health")
        # Should return 200 with default health data or 500 due to missing dependencies
        assert response.status_code in [200, 500, 503]
    
    def test_hook_executions_endpoint_exists(self, client):
        """Test that hook executions endpoint exists."""
        response = client.get("/api/v1/hooks/executions")
        # Should return 500 due to missing dependencies, but endpoint should exist
        assert response.status_code in [500, 503]
    
    def test_hook_analytics_endpoint_exists(self, client):
        """Test that hook analytics endpoint exists."""
        response = client.get("/api/v1/hooks/analytics/performance")
        # Should return 400 (bad request) or 500 due to missing dependencies
        assert response.status_code in [400, 500, 503]
    
    def test_hook_alerts_endpoint_exists(self, client):
        """Test that hook alerts endpoint exists."""
        response = client.get("/api/v1/hooks/alerts")
        # Should return 200 with empty alerts or 500 due to missing dependencies
        assert response.status_code in [200, 500, 503]
    
    def test_hook_config_teams_endpoint_exists(self, client):
        """Test that hook config teams endpoint exists."""
        response = client.get("/api/v1/hooks/config/teams")
        # Should return 200 with empty teams or 500 due to missing dependencies
        assert response.status_code in [200, 500, 503]
    
    def test_hook_stats_endpoint_exists(self, client):
        """Test that hook stats endpoint exists."""
        response = client.get("/api/v1/hooks/stats")
        # Should return 200 with default stats or 500 due to missing dependencies
        assert response.status_code in [200, 500, 503]
    
    def test_invalid_endpoint_returns_404(self, client):
        """Test that invalid endpoints return 404."""
        response = client.get("/api/v1/hooks/invalid-endpoint")
        assert response.status_code == 404
    
    def test_alert_acknowledge_endpoint_exists(self, client):
        """Test that alert acknowledge endpoint exists."""
        response = client.post("/api/v1/hooks/alerts/test-alert/acknowledge")
        # Should return 404 (alert not found) or 500 due to missing dependencies
        assert response.status_code in [404, 500, 503]
    
    def test_alert_resolve_endpoint_exists(self, client):
        """Test that alert resolve endpoint exists."""
        response = client.post("/api/v1/hooks/alerts/test-alert/resolve")
        # Should return 404 (alert not found) or 500 due to missing dependencies
        assert response.status_code in [404, 500, 503]


class TestAPIResponseStructure:
    """Test API response structure for error cases."""
    
    def test_error_response_structure(self, client):
        """Test that error responses have proper structure."""
        response = client.get("/api/v1/hooks/status")
        
        # Should return JSON error response
        assert response.headers.get("content-type") == "application/json"
        
        # Should have detail field in error response
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
    
    def test_invalid_hook_id_format(self, client):
        """Test handling of invalid hook ID format."""
        response = client.get("/api/v1/hooks/status/")
        # Should return 404 for empty hook ID or 500 due to missing dependencies
        assert response.status_code in [404, 500]
    
    def test_invalid_execution_id_format(self, client):
        """Test handling of invalid execution ID format."""
        response = client.get("/api/v1/hooks/executions/")
        # Should return 404 for empty execution ID or 500 due to missing dependencies
        assert response.status_code in [404, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])