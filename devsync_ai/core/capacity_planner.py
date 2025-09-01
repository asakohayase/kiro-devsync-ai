"""
Capacity planning with predictive scaling and resource allocation.
"""

import asyncio
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import numpy as np
from collections import defaultdict, deque

from ..database.connection import get_database_connection
from ..analytics.performance_monitor import performance_monitor, MetricType


class ResourceType(Enum):
    """Types of resources for capacity planning."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    WORKERS = "workers"
    DATABASE_CONNECTIONS = "database_connections"


class ScalingDirection(Enum):
    """Scaling direction recommendations."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"


class PredictionModel(Enum):
    """Prediction models for capacity planning."""
    LINEAR_REGRESSION = "linear_regression"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    SEASONAL_DECOMPOSITION = "seasonal_decomposition"
    MOVING_AVERAGE = "moving_average"


@dataclass
class ResourceMetric:
    """Resource utilization metric."""
    resource_type: ResourceType
    current_usage: float
    capacity: float
    utilization_percent: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapacityForecast:
    """Capacity forecast for a resource."""
    resource_type: ResourceType
    current_utilization: float
    predicted_utilization: List[float]  # Predictions for next N periods
    prediction_timestamps: List[datetime]
    confidence_intervals: List[Tuple[float, float]]  # (lower, upper) bounds
    model_used: PredictionModel
    accuracy_score: Optional[float] = None


@dataclass
class ScalingRecommendation:
    """Resource scaling recommendation."""
    resource_type: ResourceType
    current_capacity: float
    recommended_capacity: float
    scaling_direction: ScalingDirection
    urgency: str  # "low", "medium", "high", "critical"
    reasoning: str
    estimated_cost_impact: Optional[float] = None
    implementation_timeline: Optional[str] = None
    risk_assessment: Optional[str] = None


@dataclass
class CapacityAlert:
    """Capacity planning alert."""
    alert_id: str
    resource_type: ResourceType
    alert_type: str  # "threshold_exceeded", "forecast_warning", "scaling_needed"
    current_value: float
    threshold_value: float
    predicted_breach_time: Optional[datetime] = None
    severity: str = "medium"
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CapacityPlanner:
    """
    Intelligent capacity planning system with predictive scaling and resource allocation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Resource tracking
        self.resource_metrics: Dict[ResourceType, deque] = {
            resource_type: deque(maxlen=1000) for resource_type in ResourceType
        }
        
        # Capacity thresholds
        self.capacity_thresholds = {
            ResourceType.CPU: {"warning": 70.0, "critical": 85.0, "target": 60.0},
            ResourceType.MEMORY: {"warning": 75.0, "critical": 90.0, "target": 65.0},
            ResourceType.STORAGE: {"warning": 80.0, "critical": 95.0, "target": 70.0},
            ResourceType.NETWORK: {"warning": 70.0, "critical": 85.0, "target": 60.0},
            ResourceType.WORKERS: {"warning": 80.0, "critical": 95.0, "target": 70.0},
            ResourceType.DATABASE_CONNECTIONS: {"warning": 75.0, "critical": 90.0, "target": 65.0}
        }
        
        # Forecasting parameters
        self.forecast_horizon_hours = 24  # Predict 24 hours ahead
        self.forecast_intervals = 12  # 12 predictions (every 2 hours)
        self.min_data_points = 50  # Minimum data points for reliable prediction
        
        # Scaling parameters
        self.scale_up_buffer = 1.2  # 20% buffer when scaling up
        self.scale_down_buffer = 0.8  # 20% buffer when scaling down
        self.scaling_cooldown = timedelta(minutes=30)  # Minimum time between scaling actions
        
        # State tracking
        self.last_scaling_actions: Dict[ResourceType, datetime] = {}
        self.active_alerts: Dict[str, CapacityAlert] = {}
        self.scaling_history: List[Dict[str, Any]] = []
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._forecasting_task: Optional[asyncio.Task] = None
    
    async def start_planning(self):
        """Start the capacity planning system."""
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._forecasting_task = asyncio.create_task(self._forecasting_loop())
        self.logger.info("Capacity planner started")
    
    async def stop_planning(self):
        """Stop the capacity planning system."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._forecasting_task:
            self._forecasting_task.cancel()
        
        try:
            if self._monitoring_task:
                await self._monitoring_task
            if self._forecasting_task:
                await self._forecasting_task
        except asyncio.CancelledError:
            pass
        
        self.logger.info("Capacity planner stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for capacity planning."""
        try:
            while True:
                await self._collect_resource_metrics()
                await self._check_capacity_thresholds()
                await self._generate_scaling_recommendations()
                await asyncio.sleep(60)  # Monitor every minute
        except asyncio.CancelledError:
            self.logger.info("Capacity monitoring loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in capacity monitoring loop: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _forecasting_loop(self):
        """Forecasting loop for predictive capacity planning."""
        try:
            while True:
                await self._generate_capacity_forecasts()
                await self._analyze_forecast_alerts()
                await asyncio.sleep(1800)  # Generate forecasts every 30 minutes
        except asyncio.CancelledError:
            self.logger.info("Capacity forecasting loop cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in capacity forecasting loop: {e}")
            await asyncio.sleep(1800)
    
    async def _collect_resource_metrics(self):
        """Collect current resource utilization metrics."""
        try:
            # Get system health from performance monitor
            system_health = await performance_monitor.get_system_health()
            
            # CPU metrics
            cpu_metric = ResourceMetric(
                resource_type=ResourceType.CPU,
                current_usage=system_health.cpu_usage,
                capacity=100.0,
                utilization_percent=system_health.cpu_usage,
                timestamp=datetime.utcnow()
            )
            self.resource_metrics[ResourceType.CPU].append(cpu_metric)
            
            # Memory metrics
            memory_metric = ResourceMetric(
                resource_type=ResourceType.MEMORY,
                current_usage=system_health.memory_usage,
                capacity=100.0,
                utilization_percent=system_health.memory_usage,
                timestamp=datetime.utcnow()
            )
            self.resource_metrics[ResourceType.MEMORY].append(memory_metric)
            
            # Worker metrics (from load balancer if available)
            try:
                from ..core.load_balancer import load_balancer
                lb_stats = load_balancer.get_load_balancer_stats()
                
                worker_utilization = lb_stats["capacity"]["utilization_percent"]
                worker_metric = ResourceMetric(
                    resource_type=ResourceType.WORKERS,
                    current_usage=lb_stats["capacity"]["active_tasks"],
                    capacity=lb_stats["capacity"]["total_slots"],
                    utilization_percent=worker_utilization,
                    timestamp=datetime.utcnow(),
                    metadata={"healthy_workers": lb_stats["workers"]["healthy"]}
                )
                self.resource_metrics[ResourceType.WORKERS].append(worker_metric)
                
            except Exception as e:
                self.logger.debug(f"Could not collect worker metrics: {e}")
            
            # Database connection metrics
            await self._collect_database_metrics()
            
        except Exception as e:
            self.logger.error(f"Error collecting resource metrics: {e}")
    
    async def _collect_database_metrics(self):
        """Collect database connection and performance metrics."""
        try:
            async with get_database_connection() as conn:
                # Get database connection statistics
                db_stats = await conn.fetchrow("""
                    SELECT 
                        setting::int as max_connections,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT count(*) FROM pg_stat_activity) as total_connections
                    FROM pg_settings WHERE name = 'max_connections'
                """)
                
                if db_stats:
                    utilization = (db_stats['total_connections'] / db_stats['max_connections']) * 100
                    
                    db_metric = ResourceMetric(
                        resource_type=ResourceType.DATABASE_CONNECTIONS,
                        current_usage=db_stats['total_connections'],
                        capacity=db_stats['max_connections'],
                        utilization_percent=utilization,
                        timestamp=datetime.utcnow(),
                        metadata={"active_connections": db_stats['active_connections']}
                    )
                    self.resource_metrics[ResourceType.DATABASE_CONNECTIONS].append(db_metric)
                
        except Exception as e:
            self.logger.debug(f"Could not collect database metrics: {e}")
    
    async def _check_capacity_thresholds(self):
        """Check if any resources exceed capacity thresholds."""
        for resource_type, metrics in self.resource_metrics.items():
            if not metrics:
                continue
            
            latest_metric = metrics[-1]
            thresholds = self.capacity_thresholds.get(resource_type, {})
            
            # Check critical threshold
            if latest_metric.utilization_percent >= thresholds.get("critical", 95):
                await self._create_capacity_alert(
                    resource_type,
                    "threshold_exceeded",
                    latest_metric.utilization_percent,
                    thresholds["critical"],
                    "critical",
                    f"Critical {resource_type.value} utilization: {latest_metric.utilization_percent:.1f}%"
                )
            
            # Check warning threshold
            elif latest_metric.utilization_percent >= thresholds.get("warning", 80):
                await self._create_capacity_alert(
                    resource_type,
                    "threshold_exceeded",
                    latest_metric.utilization_percent,
                    thresholds["warning"],
                    "warning",
                    f"High {resource_type.value} utilization: {latest_metric.utilization_percent:.1f}%"
                )
    
    async def _create_capacity_alert(
        self,
        resource_type: ResourceType,
        alert_type: str,
        current_value: float,
        threshold_value: float,
        severity: str,
        message: str,
        predicted_breach_time: Optional[datetime] = None
    ):
        """Create a capacity planning alert."""
        alert_id = f"{resource_type.value}_{alert_type}_{int(datetime.utcnow().timestamp())}"
        
        # Don't create duplicate alerts
        existing_key = f"{resource_type.value}_{alert_type}"
        if existing_key in self.active_alerts:
            return
        
        alert = CapacityAlert(
            alert_id=alert_id,
            resource_type=resource_type,
            alert_type=alert_type,
            current_value=current_value,
            threshold_value=threshold_value,
            predicted_breach_time=predicted_breach_time,
            severity=severity,
            message=message
        )
        
        self.active_alerts[existing_key] = alert
        
        # Store alert in database
        await self._store_capacity_alert(alert)
        
        # Send notification
        await self._send_capacity_alert(alert)
        
        self.logger.warning(f"Capacity alert created: {message}")
    
    async def _store_capacity_alert(self, alert: CapacityAlert):
        """Store capacity alert in database."""
        try:
            async with get_database_connection() as conn:
                await conn.execute("""
                    INSERT INTO capacity_alerts (
                        alert_id, resource_type, alert_type, current_value, threshold_value,
                        predicted_breach_time, severity, message, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                alert.alert_id,
                alert.resource_type.value,
                alert.alert_type,
                alert.current_value,
                alert.threshold_value,
                alert.predicted_breach_time,
                alert.severity,
                alert.message,
                alert.timestamp
                )
        except Exception as e:
            self.logger.error(f"Failed to store capacity alert: {e}")
    
    async def _send_capacity_alert(self, alert: CapacityAlert):
        """Send capacity alert notification."""
        try:
            from ..core.notification_integration import NotificationIntegration
            
            notification = NotificationIntegration()
            
            emoji = "🚨" if alert.severity == "critical" else "⚠️"
            message = f"{emoji} **Capacity Alert**\n{alert.message}"
            
            if alert.predicted_breach_time:
                message += f"\nPredicted breach: {alert.predicted_breach_time.strftime('%Y-%m-%d %H:%M UTC')}"
            
            await notification.send_slack_notification(
                channel="#devsync-capacity",
                message=message,
                metadata={
                    "alert_type": "capacity_planning",
                    "resource_type": alert.resource_type.value,
                    "severity": alert.severity
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to send capacity alert: {e}")
    
    async def _generate_capacity_forecasts(self):
        """Generate capacity forecasts for all resources."""
        for resource_type, metrics in self.resource_metrics.items():
            if len(metrics) < self.min_data_points:
                continue
            
            try:
                forecast = await self._forecast_resource_utilization(resource_type, metrics)
                if forecast:
                    await self._store_capacity_forecast(forecast)
                    
            except Exception as e:
                self.logger.error(f"Error generating forecast for {resource_type.value}: {e}")
    
    async def _forecast_resource_utilization(
        self,
        resource_type: ResourceType,
        metrics: deque
    ) -> Optional[CapacityForecast]:
        """Generate capacity forecast for a specific resource."""
        if len(metrics) < self.min_data_points:
            return None
        
        # Extract utilization data
        utilization_data = [m.utilization_percent for m in metrics]
        timestamps = [m.timestamp for m in metrics]
        
        # Try different prediction models
        models_to_try = [
            PredictionModel.EXPONENTIAL_SMOOTHING,
            PredictionModel.LINEAR_REGRESSION,
            PredictionModel.MOVING_AVERAGE
        ]
        
        best_forecast = None
        best_accuracy = -1
        
        for model in models_to_try:
            try:
                forecast = await self._apply_prediction_model(
                    model, utilization_data, timestamps, resource_type
                )
                
                if forecast and forecast.accuracy_score and forecast.accuracy_score > best_accuracy:
                    best_forecast = forecast
                    best_accuracy = forecast.accuracy_score
                    
            except Exception as e:
                self.logger.debug(f"Prediction model {model.value} failed for {resource_type.value}: {e}")
        
        return best_forecast
    
    async def _apply_prediction_model(
        self,
        model: PredictionModel,
        data: List[float],
        timestamps: List[datetime],
        resource_type: ResourceType
    ) -> Optional[CapacityForecast]:
        """Apply a specific prediction model to the data."""
        if model == PredictionModel.MOVING_AVERAGE:
            return self._moving_average_forecast(data, timestamps, resource_type)
        elif model == PredictionModel.LINEAR_REGRESSION:
            return self._linear_regression_forecast(data, timestamps, resource_type)
        elif model == PredictionModel.EXPONENTIAL_SMOOTHING:
            return self._exponential_smoothing_forecast(data, timestamps, resource_type)
        else:
            return None
    
    def _moving_average_forecast(
        self,
        data: List[float],
        timestamps: List[datetime],
        resource_type: ResourceType
    ) -> CapacityForecast:
        """Generate forecast using moving average."""
        window_size = min(20, len(data) // 4)  # Use 1/4 of data or max 20 points
        
        # Calculate moving average
        moving_avg = statistics.mean(data[-window_size:])
        
        # Generate predictions (assume steady state)
        predictions = [moving_avg] * self.forecast_intervals
        
        # Generate prediction timestamps
        last_timestamp = timestamps[-1]
        interval_hours = self.forecast_horizon_hours / self.forecast_intervals
        prediction_timestamps = [
            last_timestamp + timedelta(hours=i * interval_hours)
            for i in range(1, self.forecast_intervals + 1)
        ]
        
        # Simple confidence intervals (±10% of the prediction)
        confidence_intervals = [
            (pred * 0.9, pred * 1.1) for pred in predictions
        ]
        
        # Calculate accuracy (using recent data)
        recent_data = data[-window_size:]
        accuracy = 1.0 - (statistics.stdev(recent_data) / statistics.mean(recent_data))
        accuracy = max(0, min(1, accuracy))  # Clamp between 0 and 1
        
        return CapacityForecast(
            resource_type=resource_type,
            current_utilization=data[-1],
            predicted_utilization=predictions,
            prediction_timestamps=prediction_timestamps,
            confidence_intervals=confidence_intervals,
            model_used=PredictionModel.MOVING_AVERAGE,
            accuracy_score=accuracy
        )
    
    def _linear_regression_forecast(
        self,
        data: List[float],
        timestamps: List[datetime],
        resource_type: ResourceType
    ) -> CapacityForecast:
        """Generate forecast using linear regression."""
        # Convert timestamps to numeric values (hours since first timestamp)
        base_time = timestamps[0]
        x_values = [(ts - base_time).total_seconds() / 3600 for ts in timestamps]
        y_values = data
        
        # Simple linear regression
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope and intercept
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Generate predictions
        last_x = x_values[-1]
        interval_hours = self.forecast_horizon_hours / self.forecast_intervals
        
        predictions = []
        prediction_timestamps = []
        
        for i in range(1, self.forecast_intervals + 1):
            future_x = last_x + (i * interval_hours)
            prediction = slope * future_x + intercept
            predictions.append(max(0, prediction))  # Don't predict negative utilization
            
            future_timestamp = timestamps[-1] + timedelta(hours=i * interval_hours)
            prediction_timestamps.append(future_timestamp)
        
        # Calculate confidence intervals based on residuals
        residuals = [y - (slope * x + intercept) for x, y in zip(x_values, y_values)]
        std_error = statistics.stdev(residuals) if len(residuals) > 1 else 0
        
        confidence_intervals = [
            (max(0, pred - 1.96 * std_error), pred + 1.96 * std_error)
            for pred in predictions
        ]
        
        # Calculate R-squared for accuracy
        y_mean = statistics.mean(y_values)
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum(r ** 2 for r in residuals)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return CapacityForecast(
            resource_type=resource_type,
            current_utilization=data[-1],
            predicted_utilization=predictions,
            prediction_timestamps=prediction_timestamps,
            confidence_intervals=confidence_intervals,
            model_used=PredictionModel.LINEAR_REGRESSION,
            accuracy_score=max(0, r_squared)
        )
    
    def _exponential_smoothing_forecast(
        self,
        data: List[float],
        timestamps: List[datetime],
        resource_type: ResourceType
    ) -> CapacityForecast:
        """Generate forecast using exponential smoothing."""
        alpha = 0.3  # Smoothing parameter
        
        # Apply exponential smoothing
        smoothed = [data[0]]
        for i in range(1, len(data)):
            smoothed_value = alpha * data[i] + (1 - alpha) * smoothed[i-1]
            smoothed.append(smoothed_value)
        
        # Use the last smoothed value as the forecast
        forecast_value = smoothed[-1]
        
        # Generate predictions (assume steady state with slight trend)
        trend = (smoothed[-1] - smoothed[-min(10, len(smoothed))]) / min(10, len(smoothed))
        
        predictions = []
        for i in range(1, self.forecast_intervals + 1):
            prediction = forecast_value + (trend * i)
            predictions.append(max(0, prediction))
        
        # Generate prediction timestamps
        last_timestamp = timestamps[-1]
        interval_hours = self.forecast_horizon_hours / self.forecast_intervals
        prediction_timestamps = [
            last_timestamp + timedelta(hours=i * interval_hours)
            for i in range(1, self.forecast_intervals + 1)
        ]
        
        # Calculate confidence intervals
        recent_variance = statistics.variance(data[-20:]) if len(data) >= 20 else statistics.variance(data)
        std_dev = recent_variance ** 0.5
        
        confidence_intervals = [
            (max(0, pred - 1.96 * std_dev), pred + 1.96 * std_dev)
            for pred in predictions
        ]
        
        # Calculate accuracy based on recent prediction errors
        errors = [abs(data[i] - smoothed[i]) for i in range(len(data))]
        mean_error = statistics.mean(errors[-20:]) if len(errors) >= 20 else statistics.mean(errors)
        mean_value = statistics.mean(data[-20:]) if len(data) >= 20 else statistics.mean(data)
        accuracy = 1 - (mean_error / mean_value) if mean_value > 0 else 0
        
        return CapacityForecast(
            resource_type=resource_type,
            current_utilization=data[-1],
            predicted_utilization=predictions,
            prediction_timestamps=prediction_timestamps,
            confidence_intervals=confidence_intervals,
            model_used=PredictionModel.EXPONENTIAL_SMOOTHING,
            accuracy_score=max(0, min(1, accuracy))
        )
    
    async def _store_capacity_forecast(self, forecast: CapacityForecast):
        """Store capacity forecast in database."""
        try:
            async with get_database_connection() as conn:
                await conn.execute("""
                    INSERT INTO capacity_forecasts (
                        resource_type, current_utilization, predicted_utilization,
                        prediction_timestamps, confidence_intervals, model_used,
                        accuracy_score, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                forecast.resource_type.value,
                forecast.current_utilization,
                json.dumps(forecast.predicted_utilization),
                json.dumps([ts.isoformat() for ts in forecast.prediction_timestamps]),
                json.dumps(forecast.confidence_intervals),
                forecast.model_used.value,
                forecast.accuracy_score,
                datetime.utcnow()
                )
        except Exception as e:
            self.logger.error(f"Failed to store capacity forecast: {e}")
    
    async def _analyze_forecast_alerts(self):
        """Analyze forecasts and create alerts for predicted capacity issues."""
        try:
            async with get_database_connection() as conn:
                # Get recent forecasts
                rows = await conn.fetch("""
                    SELECT resource_type, predicted_utilization, prediction_timestamps, created_at
                    FROM capacity_forecasts
                    WHERE created_at >= NOW() - INTERVAL '1 hour'
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                for row in rows:
                    resource_type = ResourceType(row['resource_type'])
                    predictions = json.loads(row['predicted_utilization'])
                    timestamps = [datetime.fromisoformat(ts) for ts in json.loads(row['prediction_timestamps'])]
                    
                    # Check if any predictions exceed thresholds
                    thresholds = self.capacity_thresholds.get(resource_type, {})
                    critical_threshold = thresholds.get("critical", 95)
                    warning_threshold = thresholds.get("warning", 80)
                    
                    for i, (prediction, timestamp) in enumerate(zip(predictions, timestamps)):
                        if prediction >= critical_threshold:
                            await self._create_capacity_alert(
                                resource_type,
                                "forecast_warning",
                                prediction,
                                critical_threshold,
                                "critical",
                                f"Predicted critical {resource_type.value} utilization: {prediction:.1f}%",
                                timestamp
                            )
                            break  # Only alert for the first predicted breach
                        elif prediction >= warning_threshold:
                            await self._create_capacity_alert(
                                resource_type,
                                "forecast_warning",
                                prediction,
                                warning_threshold,
                                "warning",
                                f"Predicted high {resource_type.value} utilization: {prediction:.1f}%",
                                timestamp
                            )
                            break
                            
        except Exception as e:
            self.logger.error(f"Error analyzing forecast alerts: {e}")
    
    async def _generate_scaling_recommendations(self):
        """Generate scaling recommendations based on current and predicted utilization."""
        recommendations = []
        
        for resource_type, metrics in self.resource_metrics.items():
            if not metrics:
                continue
            
            try:
                recommendation = await self._analyze_scaling_need(resource_type, metrics)
                if recommendation:
                    recommendations.append(recommendation)
                    
            except Exception as e:
                self.logger.error(f"Error generating scaling recommendation for {resource_type.value}: {e}")
        
        # Store and process recommendations
        for recommendation in recommendations:
            await self._process_scaling_recommendation(recommendation)
    
    async def _analyze_scaling_need(
        self,
        resource_type: ResourceType,
        metrics: deque
    ) -> Optional[ScalingRecommendation]:
        """Analyze if scaling is needed for a resource."""
        if len(metrics) < 10:
            return None
        
        latest_metric = metrics[-1]
        thresholds = self.capacity_thresholds.get(resource_type, {})
        target_utilization = thresholds.get("target", 70)
        
        current_utilization = latest_metric.utilization_percent
        current_capacity = latest_metric.capacity
        
        # Check if scaling is needed
        if current_utilization > thresholds.get("critical", 95):
            # Immediate scale up needed
            recommended_capacity = current_capacity * self.scale_up_buffer
            urgency = "critical"
            reasoning = f"Current utilization ({current_utilization:.1f}%) exceeds critical threshold"
            
        elif current_utilization > thresholds.get("warning", 80):
            # Scale up recommended
            recommended_capacity = current_capacity * 1.1  # 10% increase
            urgency = "high"
            reasoning = f"Current utilization ({current_utilization:.1f}%) exceeds warning threshold"
            
        elif current_utilization < target_utilization * 0.5:  # Very low utilization
            # Scale down possible
            recommended_capacity = current_capacity * self.scale_down_buffer
            urgency = "low"
            reasoning = f"Low utilization ({current_utilization:.1f}%) suggests over-provisioning"
            
        else:
            return None  # No scaling needed
        
        # Determine scaling direction
        if recommended_capacity > current_capacity:
            scaling_direction = ScalingDirection.SCALE_UP
        elif recommended_capacity < current_capacity:
            scaling_direction = ScalingDirection.SCALE_DOWN
        else:
            scaling_direction = ScalingDirection.MAINTAIN
        
        return ScalingRecommendation(
            resource_type=resource_type,
            current_capacity=current_capacity,
            recommended_capacity=recommended_capacity,
            scaling_direction=scaling_direction,
            urgency=urgency,
            reasoning=reasoning,
            implementation_timeline=self._estimate_implementation_timeline(urgency),
            risk_assessment=self._assess_scaling_risk(resource_type, scaling_direction)
        )
    
    def _estimate_implementation_timeline(self, urgency: str) -> str:
        """Estimate implementation timeline based on urgency."""
        timelines = {
            "critical": "Immediate (0-15 minutes)",
            "high": "Short-term (15-60 minutes)",
            "medium": "Medium-term (1-4 hours)",
            "low": "Long-term (4-24 hours)"
        }
        return timelines.get(urgency, "Medium-term (1-4 hours)")
    
    def _assess_scaling_risk(self, resource_type: ResourceType, direction: ScalingDirection) -> str:
        """Assess the risk of scaling operation."""
        if direction == ScalingDirection.SCALE_UP:
            if resource_type in [ResourceType.CPU, ResourceType.MEMORY]:
                return "Low risk - Can be done with minimal disruption"
            elif resource_type == ResourceType.WORKERS:
                return "Medium risk - May require load balancer reconfiguration"
            else:
                return "Medium risk - Requires careful coordination"
        elif direction == ScalingDirection.SCALE_DOWN:
            return "Medium risk - Ensure sufficient capacity remains"
        else:
            return "No risk - No changes required"
    
    async def _process_scaling_recommendation(self, recommendation: ScalingRecommendation):
        """Process and potentially execute a scaling recommendation."""
        # Check cooldown period
        last_action = self.last_scaling_actions.get(recommendation.resource_type)
        if last_action and datetime.utcnow() - last_action < self.scaling_cooldown:
            return  # Still in cooldown period
        
        # Store recommendation
        await self._store_scaling_recommendation(recommendation)
        
        # Auto-execute critical scaling actions
        if recommendation.urgency == "critical" and recommendation.scaling_direction == ScalingDirection.SCALE_UP:
            await self._execute_scaling_action(recommendation)
        
        # Send notification for all recommendations
        await self._send_scaling_notification(recommendation)
    
    async def _store_scaling_recommendation(self, recommendation: ScalingRecommendation):
        """Store scaling recommendation in database."""
        try:
            async with get_database_connection() as conn:
                await conn.execute("""
                    INSERT INTO scaling_recommendations (
                        resource_type, current_capacity, recommended_capacity,
                        scaling_direction, urgency, reasoning, implementation_timeline,
                        risk_assessment, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                recommendation.resource_type.value,
                recommendation.current_capacity,
                recommendation.recommended_capacity,
                recommendation.scaling_direction.value,
                recommendation.urgency,
                recommendation.reasoning,
                recommendation.implementation_timeline,
                recommendation.risk_assessment,
                datetime.utcnow()
                )
        except Exception as e:
            self.logger.error(f"Failed to store scaling recommendation: {e}")
    
    async def _execute_scaling_action(self, recommendation: ScalingRecommendation):
        """Execute automatic scaling action."""
        try:
            self.logger.info(f"Executing automatic scaling for {recommendation.resource_type.value}")
            
            # Record scaling action
            self.last_scaling_actions[recommendation.resource_type] = datetime.utcnow()
            
            # Execute scaling based on resource type
            if recommendation.resource_type == ResourceType.WORKERS:
                await self._scale_workers(recommendation)
            elif recommendation.resource_type == ResourceType.DATABASE_CONNECTIONS:
                await self._scale_database_connections(recommendation)
            
            # Record scaling history
            self.scaling_history.append({
                "resource_type": recommendation.resource_type.value,
                "action": recommendation.scaling_direction.value,
                "from_capacity": recommendation.current_capacity,
                "to_capacity": recommendation.recommended_capacity,
                "timestamp": datetime.utcnow().isoformat(),
                "automatic": True
            })
            
        except Exception as e:
            self.logger.error(f"Failed to execute scaling action: {e}")
    
    async def _scale_workers(self, recommendation: ScalingRecommendation):
        """Scale worker nodes."""
        try:
            from ..core.load_balancer import load_balancer
            
            if recommendation.scaling_direction == ScalingDirection.SCALE_UP:
                # Trigger scale up in load balancer
                await load_balancer._scale_up()
            elif recommendation.scaling_direction == ScalingDirection.SCALE_DOWN:
                # Trigger scale down in load balancer
                await load_balancer._scale_down()
                
        except Exception as e:
            self.logger.error(f"Failed to scale workers: {e}")
    
    async def _scale_database_connections(self, recommendation: ScalingRecommendation):
        """Scale database connections (placeholder - would require database configuration changes)."""
        # This would typically involve updating database configuration
        # For now, just log the recommendation
        self.logger.info(f"Database connection scaling recommended: {recommendation.reasoning}")
    
    async def _send_scaling_notification(self, recommendation: ScalingRecommendation):
        """Send scaling recommendation notification."""
        try:
            from ..core.notification_integration import NotificationIntegration
            
            notification = NotificationIntegration()
            
            emoji = "🚨" if recommendation.urgency == "critical" else "📊"
            direction_emoji = "⬆️" if recommendation.scaling_direction == ScalingDirection.SCALE_UP else "⬇️"
            
            message = (
                f"{emoji} **Scaling Recommendation**\n"
                f"Resource: {recommendation.resource_type.value.title()}\n"
                f"Direction: {direction_emoji} {recommendation.scaling_direction.value.replace('_', ' ').title()}\n"
                f"Current: {recommendation.current_capacity:.1f}\n"
                f"Recommended: {recommendation.recommended_capacity:.1f}\n"
                f"Urgency: {recommendation.urgency.title()}\n"
                f"Reason: {recommendation.reasoning}\n"
                f"Timeline: {recommendation.implementation_timeline}"
            )
            
            await notification.send_slack_notification(
                channel="#devsync-capacity",
                message=message,
                metadata={
                    "alert_type": "scaling_recommendation",
                    "resource_type": recommendation.resource_type.value,
                    "urgency": recommendation.urgency
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to send scaling notification: {e}")
    
    def get_capacity_summary(self) -> Dict[str, Any]:
        """Get comprehensive capacity planning summary."""
        summary = {
            "current_utilization": {},
            "active_alerts": len(self.active_alerts),
            "scaling_history": len(self.scaling_history),
            "forecast_accuracy": {}
        }
        
        # Current utilization for each resource
        for resource_type, metrics in self.resource_metrics.items():
            if metrics:
                latest = metrics[-1]
                summary["current_utilization"][resource_type.value] = {
                    "utilization_percent": round(latest.utilization_percent, 2),
                    "capacity": latest.capacity,
                    "current_usage": latest.current_usage,
                    "timestamp": latest.timestamp.isoformat()
                }
        
        # Recent scaling actions
        summary["recent_scaling_actions"] = self.scaling_history[-5:] if self.scaling_history else []
        
        # Active alerts by severity
        alert_summary = {"critical": 0, "warning": 0, "info": 0}
        for alert in self.active_alerts.values():
            alert_summary[alert.severity] = alert_summary.get(alert.severity, 0) + 1
        summary["alerts_by_severity"] = alert_summary
        
        return summary


# Global capacity planner instance
capacity_planner = CapacityPlanner()