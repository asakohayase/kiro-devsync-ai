import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# Import Slack SDK
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    print("⚠️ slack_sdk not installed. Install with: pip install slack-sdk")

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealSlackClient:
    """Real Slack client using slack-sdk"""
    
    def __init__(self):
        self.token = os.getenv("SLACK_BOT_TOKEN")
        if not self.token:
            logger.error("SLACK_BOT_TOKEN not found in environment variables")
            raise ValueError("SLACK_BOT_TOKEN is required")
        
        if SLACK_SDK_AVAILABLE:
            self.client = WebClient(token=self.token)
        else:
            self.client = None
            logger.warning("Slack SDK not available - messages will be logged only")
    
    async def send_message(self, channel: str, text: str, blocks: Optional[list] = None):
        """Send message to Slack channel"""
        try:
            if not self.client:
                logger.info(f"SLACK MESSAGE (SDK not available): {channel}: {text}")
                return {"ok": True, "simulated": True}
            
            # Remove # from channel if present and not a channel ID
            if channel.startswith("#"):
                channel = channel[1:]
            
            result = self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks
            )
            
            logger.info(f"✅ Slack message sent to #{channel}")
            return result
            
        except SlackApiError as e:
            logger.error(f"❌ Slack API error: {e.response['error']}")
            # Don't raise - log the error but continue
            return {"ok": False, "error": e.response['error']}
        except Exception as e:
            logger.error(f"❌ Slack client error: {str(e)}")
            return {"ok": False, "error": str(e)}

# Create FastAPI app
app = FastAPI(
    title="DevSync AI - GitHub Webhook Server",
    description="GitHub webhook server for DevSync AI automation",
    version="1.0.0"
)

# Initialize Slack client
try:
    slack_client = RealSlackClient()
    logger.info("✅ Slack client initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Slack client: {e}")
    slack_client = None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DevSync AI GitHub Webhook Server",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhooks/github"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "slack_configured": slack_client is not None,
        "slack_sdk_available": SLACK_SDK_AVAILABLE
    }
    
    # Test Slack connection if available
    if slack_client and slack_client.client:
        try:
            auth_result = slack_client.client.auth_test()
            status["slack_connection"] = "ok"
            status["bot_name"] = auth_result.get("user", "unknown")
        except Exception as e:
            status["slack_connection"] = "error"
            status["slack_error"] = str(e)
    
    return status

@app.post("/webhooks/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook events - MAIN ENDPOINT"""
    try:
        # Get event type from headers
        event_type = request.headers.get("X-GitHub-Event", "unknown")
        delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
        content_type = request.headers.get("content-type", "")
        
        # DEBUG: Log all headers and body preview
        headers_dict = dict(request.headers)
        logger.info(f"🚀 Webhook Headers: {headers_dict}")
        
        # Get raw body for debugging
        raw_body = await request.body()
        logger.info(f"📦 Raw body preview (first 200 chars): {raw_body[:200]}")
        
        logger.info(f"🚀 Received GitHub webhook: {event_type} (ID: {delivery_id})")
        
        # Validate content type
        if not content_type.startswith("application/json"):
            logger.error(f"❌ Invalid content type: {content_type}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Expected application/json, got {content_type}"}
            )
        
        # Parse payload
        try:
            # Parse JSON directly (FastAPI handles body reading automatically)
            payload = await request.json()
            logger.info(f"✅ Successfully parsed JSON payload")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON payload: {e}")
            logger.error(f"❌ Raw body that failed: {raw_body}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {str(e)}")
        
        # Log payload info (without sensitive data)
        action = payload.get("action", "no-action")
        logger.info(f"📋 Event: {event_type}.{action}")
        
        # Process pull request events
        if event_type == "pull_request":
            success = await process_pull_request(payload, action)
            if success:
                return JSONResponse({
                    "status": "success",
                    "message": f"Processed {event_type}.{action}",
                    "delivery_id": delivery_id
                })
            else:
                return JSONResponse({
                    "status": "processed",
                    "message": f"Received {event_type}.{action} but no notification sent",
                    "delivery_id": delivery_id
                })
        
        # Handle ping events (GitHub webhook test)
        elif event_type == "ping":
            logger.info("🏓 Ping event received - webhook is connected!")
            return JSONResponse({
                "status": "pong",
                "message": "DevSync AI webhook is working!",
                "delivery_id": delivery_id
            })
        
        # Other events - just acknowledge
        else:
            logger.info(f"ℹ️ Event {event_type} received but not processed")
            return JSONResponse({
                "status": "acknowledged",
                "message": f"Event {event_type} received",
                "delivery_id": delivery_id
            })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Add a simple test endpoint
@app.post("/test")
async def test_endpoint(request: Request):
    """Simple test endpoint to verify server is working"""
    try:
        body = await request.body()
        headers = dict(request.headers)
        
        return JSONResponse({
            "status": "test_success",
            "message": "Test endpoint working",
            "headers": headers,
            "body_length": len(body),
            "body_preview": body[:100].decode('utf-8', errors='ignore') if body else "empty"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Test failed: {str(e)}"}
        )

# ALSO add the old endpoint for compatibility
@app.post("/webhook/github")
async def github_webhook_alt(request: Request):
    """Alternative webhook endpoint for compatibility"""
    logger.info("📍 Request received on /webhook/github - redirecting to main handler")
    return await github_webhook(request)

async def process_pull_request(payload: Dict[str, Any], action: str) -> bool:
    """Process pull request events and send Slack notifications"""
    try:
        if not slack_client:
            logger.warning("⚠️ Slack client not available - cannot send notifications")
            return False
        
        # Extract PR data
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        
        if not pr or not repo:
            logger.error("❌ Missing PR or repository data in payload")
            return False
        
        # Extract key information
        pr_number = pr.get("number", 0)
        pr_title = pr.get("title", "Unknown PR")
        pr_url = pr.get("html_url", "")
        pr_author = pr.get("user", {}).get("login", "Unknown")
        pr_author_avatar = pr.get("user", {}).get("avatar_url", "")
        repo_name = repo.get("full_name", "unknown/repo")
        
        # Get branch info
        head_branch = pr.get("head", {}).get("ref", "unknown")
        base_branch = pr.get("base", {}).get("ref", "main")
        
        logger.info(f"📋 Processing PR #{pr_number}: {pr_title} by {pr_author}")
        
        # Create message based on action
        message = create_slack_message(
            action=action,
            pr_number=pr_number,
            pr_title=pr_title,
            pr_url=pr_url,
            pr_author=pr_author,
            repo_name=repo_name,
            head_branch=head_branch,
            base_branch=base_branch,
            merged=pr.get("merged", False)
        )
        
        if not message:
            logger.info(f"ℹ️ No notification needed for action: {action}")
            return False
        
        # Send to Slack
        channel = os.getenv("SLACK_CHANNEL", "general")
        result = await slack_client.send_message(
            channel=channel,
            text=message
        )
        
        if result.get("ok"):
            logger.info(f"✅ Slack notification sent for PR #{pr_number}")
            return True
        else:
            logger.error(f"❌ Slack notification failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error processing PR event: {str(e)}", exc_info=True)
        return False

def create_slack_message(action: str, pr_number: int, pr_title: str, pr_url: str, 
                        pr_author: str, repo_name: str, head_branch: str, 
                        base_branch: str, merged: bool = False) -> Optional[str]:
    """Create Slack message based on PR action"""
    
    # Define which actions to notify about and their emojis
    action_config = {
        "opened": {"emoji": "🚀", "text": "New Pull Request opened"},
        "closed": {"emoji": "✅" if merged else "❌", "text": "Pull Request merged" if merged else "Pull Request closed"},
        "reopened": {"emoji": "🔄", "text": "Pull Request reopened"},
        "ready_for_review": {"emoji": "👀", "text": "Pull Request ready for review"},
        "synchronize": {"emoji": "🔄", "text": "Pull Request updated with new commits"},
        "review_requested": {"emoji": "👥", "text": "Review requested"},
    }
    
    config = action_config.get(action)
    if not config:
        return None  # Don't notify for other actions
    
    emoji = config["emoji"]
    action_text = config["text"]
    
    # Create the message
    message = f"""{emoji} **{action_text}**

**{pr_title}** (#{pr_number})
👤 Author: {pr_author}
🏢 Repository: {repo_name}
🌿 Branch: `{head_branch}` → `{base_branch}`
🔗 Link: {pr_url}

_DevSync AI notification_"""
    
    return message

# Development server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting DevSync AI webhook server on port {port}")
    logger.info(f"📍 Webhook URL will be: http://localhost:{port}/webhooks/github")
    
    # Log configuration
    logger.info(f"🔧 Configuration:")
    logger.info(f"   - Slack Bot Token: {'✅ Set' if os.getenv('SLACK_BOT_TOKEN') else '❌ Missing'}")
    logger.info(f"   - Slack Channel: {os.getenv('SLACK_CHANNEL', 'general')}")
    logger.info(f"   - Slack SDK Available: {'✅' if SLACK_SDK_AVAILABLE else '❌'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )