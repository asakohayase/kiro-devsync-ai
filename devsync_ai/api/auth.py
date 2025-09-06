"""Authentication utilities for API routes."""

import os
import logging
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from devsync_ai.config import settings

logger = logging.getLogger(__name__)

# Security scheme for API authentication
security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> bool:
    """Verify API key authentication."""
    if not settings.api_key:
        return True  # No API key required

    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")

    if credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True