# Enhanced MessageTemplateFactory Documentation

## Overview

The Enhanced MessageTemplateFactory provides a comprehensive, production-ready system for creating, managing, and monitoring Slack message templates. Built on top of the base template system, it offers advanced features like intelligent caching, A/B testing, performance monitoring, and dynamic template registration.

## Key Features

### 🚀 **Advanced Template Management**
- Dynamic template registration and versioning
- Template inheritance and configuration
- Environment-specific template selection
- Feature flag-based template activation

### ⚡ **Intelligent Caching**
- LRU (Least Recently Used) cache eviction
- User-specific cache keys
- Configurable TTL (Time To Live)
- Cache statistics and monitoring

### 🧪 **A/B Testing**
- Consistent user assignment to variants
- Weighted template distribution
- Performance comparison between variants
- Easy variant management

### 📊 **Performance Monitoring**
- Real-time performance metrics
- Slow template alerts
- Cache hit rate tracking
- Health check endpoints

### 🎛️ **Configuration Management**
- YAML/JSON configuration support
- Environment-specific settings
- Feature flag management
- Team branding integration

## Architecture

```
MessageTemplateFactory
├── Template Registry
│   ├── Template Configurations
│   ├── Version Management
│   └── A/B Test Variants
├── Caching System
│   ├── LRU Cache
│   ├── TTL Management
│   └── Statistics Tracking
├── Performance Monitor
│   ├── Metrics Collection
│   ├── Alert System
│   └── Health Checks
└── Configuration Manager
    ├── Environment Settings
    ├── Feature Flags
    └── Team Branding
```

## Basic Usage

### Factory Creation

```python
from devsync_ai.services.template_factory import MessageTemplateFactory

# Basic factory
factory = MessageTemplateFactory()

# Factory with custom cache configuration
cache_config = {"max_size": 500, "default_ttl": 1800}
factory = MessageTemplateFactory(cache_config=cache_config)

# Factory with configuration file
factory = MessageTemplateFactory(config_path="config/templates.yaml")
```

### Template Creation

```python
# Simple template creation
template = factory.get_template("standup", standup_data)
message = template.render()

# With enhanced context
template = factory.get_template(
    "standup", 
    standup_data,
    user_id="U123456",
    channel_config=channel_config,
    user_preferences=user_preferences
)

# Convenience method
message = factory.render_template("standup", standup_data, user_id="U123456")
```

## Advanced Features

### Template Registration

```python
from devsync_ai.services.template_factory import TemplateConfig, TemplateVersion
from devsync_ai.core.base_template import MessagePriority

# Register custom template class
config = TemplateConfig(
    name="custom_notification_v2",
    template_class=CustomNotificationTemplate,
    version=TemplateVersion.BETA,
    enabled=True,
    weight=100,
    priority=MessagePriority.HIGH,
    cache_ttl=1800,
    performance_threshold=0.5,
    feature_flags=["enhanced_notifications"],
    team_branding=custom_branding
)

factory.register_template("notification", config)

# Register factory function
def custom_factory(data):
    return {
        "blocks": [...],
        "text": "Custom message"
    }

config = TemplateConfig(
    name="custom_factory",
    factory_function=custom_factory,
    version=TemplateVersion.STABLE
)

factory.register_template("custom", config)
```

### A/B Testing

```python
# Register multiple variants
variant_a = TemplateConfig(
    name="notification_v1",
    template_class=NotificationV1Template,
    weight=30  # 30% of users
)

variant_b = TemplateConfig(
    name="notification_v2", 
    template_class=NotificationV2Template,
    weight=70  # 70% of users
)

factory.register_template("notification", variant_a)
factory.register_template("notification", variant_b)

# Users will be consistently assigned to variants
template = factory.get_template("notification", data, user_id="user123")
```

### Feature Flags

```python
# Set feature flags
factory.set_feature_flag("enhanced_ui", True)
factory.set_feature_flag("beta_features", False)

# Register template with feature requirements
config = TemplateConfig(
    name="enhanced_template",
    template_class=EnhancedTemplate,
    feature_flags=["enhanced_ui", "beta_features"]
)

factory.register_template("enhanced", config)

# Template will only be available when all required flags are enabled
```

### Environment Configuration

```python
# Set environment
factory.set_environment("staging")

# Register environment-specific templates
staging_config = TemplateConfig(
    name="staging_template",
    template_class=StagingTemplate,
    environment="staging"
)

production_config = TemplateConfig(
    name="production_template",
    template_class=ProductionTemplate,
    environment="production"
)

factory.register_template("env_specific", staging_config)
factory.register_template("env_specific", production_config)
```

### Team Branding

```python
from devsync_ai.core.base_template import create_team_branding

# Set global branding
branding = create_team_branding(
    "Engineering Team",
    primary_color="#1f77b4",
    footer_text="Engineering Team • Building the Future",
    custom_emojis={"success": ":white_check_mark:"}
)

factory.set_global_branding(branding)

# Template-specific branding
config = TemplateConfig(
    name="branded_template",
    template_class=BrandedTemplate,
    team_branding=specific_branding
)
```

## Configuration Files

### YAML Configuration

```yaml
# config/templates.yaml
environment: "production"

feature_flags:
  enhanced_ui: true
  beta_features: false
  a_b_testing: true

cache:
  max_size: 1000
  default_ttl: 3600

templates:
  standup:
    - name: "standard_standup"
      version: "stable"
      enabled: true
      weight: 70
      cache_ttl: 1800
      performance_threshold: 1.0
    
    - name: "enhanced_standup"
      version: "beta"
      enabled: true
      weight: 30
      feature_flags: ["enhanced_ui"]
      cache_ttl: 900
      performance_threshold: 0.5

  notification:
    - name: "standard_notification"
      version: "stable"
      enabled: true
      weight: 100
      environment: "production"
```

### JSON Configuration

```json
{
  "environment": "staging",
  "feature_flags": {
    "enhanced_ui": true,
    "beta_features": true
  },
  "cache": {
    "max_size": 500,
    "default_ttl": 1800
  },
  "templates": {
    "alert": [
      {
        "name": "standard_alert",
        "version": "stable",
        "enabled": true,
        "weight": 100,
        "priority": "high",
        "performance_threshold": 0.8
      }
    ]
  }
}
```

## Monitoring and Analytics

### Metrics Collection

```python
# Get comprehensive metrics
metrics = factory.get_metrics()

# Template-specific metrics
for template_key, template_metrics in metrics["templates"].items():
    print(f"{template_key}:")
    print(f"  Renders: {template_metrics['render_count']}")
    print(f"  Avg Time: {template_metrics['average_render_time']:.4f}s")
    print(f"  Error Rate: {template_metrics['error_rate']:.2%}")
    print(f"  Cache Hit Rate: {template_metrics['cache_hit_rate']:.2%}")

# Cache statistics
cache_stats = metrics["cache"]
print(f"Cache Hit Rate: {cache_stats['hit_rate']:.2%}")
print(f"Cache Size: {cache_stats['size']}/{cache_stats['max_size']}")
```

### Health Monitoring

```python
# Perform health check
health = factory.health_check()

print(f"Health Score: {health['health_score']}/100")
print(f"Status: {health['status']}")
print(f"Total Renders: {health['total_renders']}")

if health['issues']:
    print(f"Issues: {', '.join(health['issues'])}")
```

### Performance Alerts

```python
# Get recent performance alerts
alerts = factory.get_performance_alerts(limit=10)

for alert in alerts:
    print(f"Slow template: {alert['template_key']}")
    print(f"Render time: {alert['render_time']:.3f}s")
    print(f"Threshold: {alert['threshold']:.3f}s")
    print(f"Time: {alert['timestamp']}")
```

## Template Interface

All templates returned by the factory implement the `TemplateInterface`:

```python
class TemplateInterface(Protocol):
    def render(self) -> Dict[str, Any]:
        """Render the template to Slack message format."""
        ...
    
    def get_fallback_text(self) -> str:
        """Get fallback text for the template."""
        ...
    
    def get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data for the template."""
        ...
    
    def has_errors(self) -> bool:
        """Check if template has errors."""
        ...
    
    def get_errors(self) -> List[str]:
        """Get template errors."""
        ...
```

### Usage Example

```python
template = factory.get_template("standup", data, user_id="U123456")

# Render the template
message = template.render()

# Get analytics
analytics = template.get_analytics_data()

# Check for errors
if template.has_errors():
    errors = template.get_errors()
    print(f"Template errors: {errors}")

# Get fallback text
fallback = template.get_fallback_text()
```

## Caching System

### Cache Configuration

```python
# Configure cache
cache_config = {
    "max_size": 1000,      # Maximum number of cached items
    "default_ttl": 3600    # Default TTL in seconds (1 hour)
}

factory = MessageTemplateFactory(cache_config=cache_config)
```

### Cache Management

```python
# Clear cache
factory.clear_cache()

# Get cache statistics
metrics = factory.get_metrics()
cache_stats = metrics["cache"]

print(f"Hit Rate: {cache_stats['hit_rate']:.2%}")
print(f"Size: {cache_stats['size']}/{cache_stats['max_size']}")
print(f"Hits: {cache_stats['hits']}")
print(f"Misses: {cache_stats['misses']}")
print(f"Evictions: {cache_stats['evictions']}")
```

### Cache Keys

Cache keys are generated based on:
- Template type
- Template data (JSON serialized)
- User ID (for personalized caching)

This ensures that different users get appropriate cached results while maximizing cache efficiency.

## Error Handling

### Template Errors

```python
try:
    template = factory.get_template("unknown_type", data)
except ValueError as e:
    print(f"Template not found: {e}")

# Check template errors
template = factory.get_template("standup", data)
if template.has_errors():
    errors = template.get_errors()
    for error in errors:
        print(f"Template error: {error}")
```

### Performance Issues

```python
# Monitor for slow templates
alerts = factory.get_performance_alerts()
for alert in alerts:
    if alert['render_time'] > 1.0:  # Slower than 1 second
        print(f"Slow template detected: {alert['template_key']}")
        print(f"Consider optimizing or increasing threshold")
```

## Best Practices

### 1. Template Design

```python
# Use appropriate cache TTL based on data volatility
config = TemplateConfig(
    name="real_time_data",
    template_class=RealTimeTemplate,
    cache_ttl=60  # 1 minute for real-time data
)

config = TemplateConfig(
    name="static_content",
    template_class=StaticTemplate,
    cache_ttl=86400  # 24 hours for static content
)
```

### 2. Performance Optimization

```python
# Set appropriate performance thresholds
config = TemplateConfig(
    name="complex_template",
    template_class=ComplexTemplate,
    performance_threshold=2.0  # Allow 2 seconds for complex templates
)

config = TemplateConfig(
    name="simple_template",
    template_class=SimpleTemplate,
    performance_threshold=0.1  # Expect 100ms for simple templates
)
```

### 3. A/B Testing

```python
# Use meaningful variant names
variant_a = TemplateConfig(
    name="notification_compact",
    template_class=CompactNotificationTemplate,
    weight=50
)

variant_b = TemplateConfig(
    name="notification_detailed",
    template_class=DetailedNotificationTemplate,
    weight=50
)

# Monitor variant performance
metrics = factory.get_metrics()
for template_key, template_metrics in metrics["templates"].items():
    if "notification_" in template_key:
        print(f"{template_key}: {template_metrics['average_render_time']:.4f}s")
```

### 4. Feature Flag Management

```python
# Use descriptive feature flag names
factory.set_feature_flag("enhanced_standup_metrics", True)
factory.set_feature_flag("experimental_ai_summaries", False)
factory.set_feature_flag("mobile_optimized_layouts", True)

# Group related features
config = TemplateConfig(
    name="mobile_optimized_standup",
    template_class=MobileStandupTemplate,
    feature_flags=["mobile_optimized_layouts", "enhanced_standup_metrics"]
)
```

## Integration Examples

### Slack Bot Integration

```python
import slack_sdk

class SlackNotificationService:
    def __init__(self, slack_token: str):
        self.client = slack_sdk.WebClient(token=slack_token)
        self.factory = MessageTemplateFactory(config_path="config/templates.yaml")
        
        # Set up team branding
        branding = create_team_branding("Engineering Team")
        self.factory.set_global_branding(branding)
    
    def send_standup(self, channel: str, standup_data: dict, user_id: str):
        """Send daily standup message."""
        try:
            template = self.factory.get_template(
                "standup", 
                standup_data, 
                user_id=user_id
            )
            message = template.render()
            
            response = self.client.chat_postMessage(
                channel=channel,
                **message
            )
            
            # Log analytics
            analytics = template.get_analytics_data()
            self._log_analytics("standup_sent", analytics)
            
            return response
            
        except Exception as e:
            self._handle_error("standup_send_failed", str(e))
            raise
    
    def send_pr_notification(self, channel: str, pr_data: dict, user_id: str):
        """Send PR notification."""
        template = self.factory.get_template("pr_update", pr_data, user_id=user_id)
        message = template.render()
        
        return self.client.chat_postMessage(channel=channel, **message)
    
    def get_health_status(self) -> dict:
        """Get service health status."""
        return self.factory.health_check()
    
    def _log_analytics(self, event: str, data: dict):
        """Log analytics data."""
        # Implement your analytics logging here
        pass
    
    def _handle_error(self, error_type: str, error_message: str):
        """Handle service errors."""
        # Implement your error handling here
        pass
```

### Webhook Integration

```python
from flask import Flask, request, jsonify

app = Flask(__name__)
factory = MessageTemplateFactory()

@app.route('/webhook/github', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events."""
    payload = request.json
    
    if payload.get('action') in ['opened', 'closed', 'merged']:
        pr_data = {
            "pr": {
                "id": payload['pull_request']['number'],
                "title": payload['pull_request']['title'],
                "author": payload['pull_request']['user']['login'],
                "action": payload['action']
            }
        }
        
        template = factory.get_template("pr_update", pr_data)
        message = template.render()
        
        # Send to Slack
        send_to_slack(message)
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "ignored"})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    health = factory.health_check()
    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code

@app.route('/metrics', methods=['GET'])
def metrics():
    """Metrics endpoint."""
    return jsonify(factory.get_metrics())
```

## Troubleshooting

### Common Issues

**Templates not rendering:**
```python
# Check if template is registered
registered = factory.get_registered_templates()
if "my_template" not in registered:
    print("Template not registered")

# Check feature flags
if template_config.feature_flags:
    for flag in template_config.feature_flags:
        if not factory._feature_flags.get(flag):
            print(f"Feature flag {flag} not enabled")
```

**Poor cache performance:**
```python
# Check cache hit rate
metrics = factory.get_metrics()
hit_rate = metrics["cache"]["hit_rate"]

if hit_rate < 0.5:  # Less than 50%
    print("Consider:")
    print("- Increasing cache size")
    print("- Adjusting TTL values")
    print("- Reviewing data volatility")
```

**Slow template rendering:**
```python
# Check performance alerts
alerts = factory.get_performance_alerts()
for alert in alerts:
    print(f"Slow template: {alert['template_key']}")
    print(f"Time: {alert['render_time']:.3f}s")
    print("Consider optimizing template logic")
```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Factory will log detailed information
factory = MessageTemplateFactory()
template = factory.get_template("standup", data)
```

## Migration Guide

### From Basic Factory

```python
# Old way
from devsync_ai.services.template_factory import get_factory
factory = get_factory()
message = factory.render_template("standup", data)

# New way
from devsync_ai.services.template_factory import MessageTemplateFactory
factory = MessageTemplateFactory()
template = factory.get_template("standup", data, user_id="U123456")
message = template.render()
analytics = template.get_analytics_data()
```

### Benefits of Enhanced Factory

- **Performance**: Intelligent caching reduces render times
- **Reliability**: Health monitoring and error tracking
- **Flexibility**: A/B testing and feature flags
- **Observability**: Comprehensive metrics and analytics
- **Scalability**: Efficient resource usage and monitoring

## Future Enhancements

- **Machine Learning**: Template performance optimization
- **Real-time Analytics**: Live performance dashboards
- **Advanced A/B Testing**: Statistical significance testing
- **Template Marketplace**: Shared template repository
- **Visual Editor**: GUI-based template creation
- **Multi-tenant Support**: Organization-specific templates