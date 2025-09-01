"""
Demonstration of the Intelligent Scheduling and Orchestration System

This example shows how to use the IntelligentScheduler for weekly changelog generation
with various scheduling scenarios including timezone awareness, holiday management,
and global team coordination.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import List

from devsync_ai.core.intelligent_scheduler import (
    IntelligentScheduler,
    ScheduleConfig,
    ScheduleFrequency,
    RetryPolicy,
    ApprovalWorkflow,
    ConflictResolution
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_basic_scheduling():
    """Demonstrate basic changelog scheduling"""
    print("\n=== Basic Scheduling Demo ===")
    
    scheduler = IntelligentScheduler()
    
    # Create a basic schedule configuration
    config = ScheduleConfig(
        team_id="engineering-team",
        frequency=ScheduleFrequency.WEEKLY,
        timezone="America/New_York",
        preferred_time=time(17, 0),  # 5 PM
        holiday_calendar="US",
        enabled=True
    )
    
    try:
        # Schedule changelog generation
        result = await scheduler.schedule_changelog_generation(config)
        print(f"✅ Scheduled changelog for team: {config.team_id}")
        print(f"   Schedule ID: {result.schedule_id}")
        print(f"   Scheduled time: {result.scheduled_time}")
        print(f"   Status: {result.status.value}")
        print(f"   Confidence: {result.metadata.get('confidence_score', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Scheduling failed: {e}")


async def demo_timezone_scheduling():
    """Demonstrate timezone-aware scheduling for global teams"""
    print("\n=== Timezone-Aware Scheduling Demo ===")
    
    scheduler = IntelligentScheduler()
    
    # Different teams in different timezones
    team_configs = [
        ScheduleConfig(
            team_id="us-west-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="America/Los_Angeles",
            preferred_time=time(16, 0),  # 4 PM PST
            holiday_calendar="US"
        ),
        ScheduleConfig(
            team_id="europe-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="Europe/London",
            preferred_time=time(17, 0),  # 5 PM GMT
            holiday_calendar="UK"
        ),
        ScheduleConfig(
            team_id="asia-team",
            frequency=ScheduleFrequency.WEEKLY,
            timezone="Asia/Tokyo",
            preferred_time=time(18, 0),  # 6 PM JST
            holiday_calendar="Japan"
        )
    ]
    
    for config in team_configs:
        try:
            # Optimize timing for each team
            optimal_timing = await scheduler.optimize_timing_for_team(config.team_id)
            print(f"✅ Optimized timing for {config.team_id}:")
            print(f"   Recommended time: {optimal_timing.recommended_time}")
            print(f"   Confidence: {optimal_timing.confidence_score:.2f}")
            print(f"   Reasoning: {optimal_timing.reasoning}")
            
        except Exception as e:
            print(f"❌ Optimization failed for {config.team_id}: {e}")


async def demo_retry_logic():
    """Demonstrate retry logic with exponential backoff"""
    print("\n=== Retry Logic Demo ===")
    
    scheduler = IntelligentScheduler()
    
    # Create a configuration with retry policy
    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay=60,  # 1 minute
        max_delay=3600,  # 1 hour
        exponential_base=2.0,
        jitter=True
    )
    
    config = ScheduleConfig(
        team_id="retry-demo-team",
        frequency=ScheduleFrequency.WEEKLY,
        timezone="UTC",
        preferred_time=time(17, 0),
        retry_policy=retry_policy
    )
    
    # Simulate a failed job
    from devsync_ai.core.intelligent_scheduler import ScheduleResult, ScheduleStatus
    
    failed_job = ScheduleResult(
        schedule_id="demo-failed-job",
        status=ScheduleStatus.FAILED,
        scheduled_time=datetime.now(),
        retry_count=0,
        error_message="Simulated failure for demo",
        metadata={"team_id": "retry-demo-team"}
    )
    
    # Add the config to scheduler
    scheduler._schedules["retry-demo-team"] = config
    
    print(f"Original failure: {failed_job.error_message}")
    
    # Simulate retry attempts
    current_job = failed_job
    for attempt in range(retry_policy.max_attempts + 1):
        try:
            result = await scheduler.manage_retry_logic(current_job)
            
            if result.status == ScheduleStatus.RETRYING:
                print(f"🔄 Retry {result.retry_count}/{retry_policy.max_attempts}")
                print(f"   Next attempt in: {result.metadata.get('retry_delay_seconds', 'N/A')} seconds")
                current_job = result
            elif result.status == ScheduleStatus.FAILED:
                print(f"❌ Permanently failed after {result.retry_count} attempts")
                print(f"   Final error: {result.error_message}")
                break
                
        except Exception as e:
            print(f"❌ Retry management failed: {e}")
            break


async def demo_manual_trigger():
    """Demonstrate manual trigger with approval workflow"""
    print("\n=== Manual Trigger Demo ===")
    
    scheduler = IntelligentScheduler()
    
    # Create configuration with approval workflow
    approval_workflow = ApprovalWorkflow(
        required=True,
        approvers=["manager@company.com", "lead@company.com"],
        timeout_minutes=60,
        auto_approve_roles=["admin", "release-manager"]
    )
    
    config = ScheduleConfig(
        team_id="manual-trigger-team",
        frequency=ScheduleFrequency.WEEKLY,
        timezone="UTC",
        preferred_time=time(17, 0),
        approval_workflow=approval_workflow
    )
    
    # Add config to scheduler
    scheduler._schedules["manual-trigger-team"] = config
    
    try:
        # Trigger manual generation
        result = await scheduler.trigger_manual_generation(
            team_id="manual-trigger-team",
            requester_id="developer@company.com",
            reason="Emergency hotfix release",
            bypass_approval=False
        )
        
        print(f"✅ Manual trigger initiated:")
        print(f"   Schedule ID: {result.schedule_id}")
        print(f"   Requester: {result.metadata.get('requester_id')}")
        print(f"   Reason: {result.metadata.get('reason')}")
        print(f"   Status: {result.status.value}")
        print(f"   Approval required: {result.metadata.get('approval_required')}")
        
    except Exception as e:
        print(f"❌ Manual trigger failed: {e}")


async def demo_global_coordination():
    """Demonstrate global team coordination"""
    print("\n=== Global Team Coordination Demo ===")
    
    scheduler = IntelligentScheduler()
    
    # List of global teams
    global_teams = [
        "americas-team",
        "europe-team", 
        "asia-pacific-team",
        "india-team"
    ]
    
    try:
        # Coordinate scheduling across all teams
        global_schedule = await scheduler.coordinate_global_teams(global_teams)
        
        print(f"✅ Global coordination completed:")
        print(f"   Schedule ID: {global_schedule.schedule_id}")
        print(f"   Teams: {', '.join(global_schedule.teams)}")
        print(f"   Coordination window: {global_schedule.coordination_window[0]} to {global_schedule.coordination_window[1]}")
        print(f"   Success probability: {global_schedule.success_probability:.2f}")
        print(f"   Conflicts detected: {len(global_schedule.conflicts)}")
        
        print("\n   Optimal times per team:")
        for team, optimal_time in global_schedule.optimal_times.items():
            print(f"     {team}: {optimal_time}")
            
    except Exception as e:
        print(f"❌ Global coordination failed: {e}")


async def demo_holiday_handling():
    """Demonstrate holiday detection and schedule adjustment"""
    print("\n=== Holiday Handling Demo ===")
    
    scheduler = IntelligentScheduler()
    
    # Create a schedule that falls on a holiday
    from devsync_ai.core.intelligent_scheduler import ScheduleResult, ScheduleStatus
    
    holiday_schedule = ScheduleResult(
        schedule_id="holiday-demo",
        status=ScheduleStatus.PENDING,
        scheduled_time=datetime(2024, 12, 25, 17, 0),  # Christmas Day
        metadata={"team_id": "holiday-demo-team"}
    )
    
    # Create team config
    config = ScheduleConfig(
        team_id="holiday-demo-team",
        frequency=ScheduleFrequency.WEEKLY,
        timezone="America/New_York",
        preferred_time=time(17, 0),
        holiday_calendar="US"
    )
    
    scheduler._schedules["holiday-demo-team"] = config
    
    try:
        # Handle holiday adjustment
        adjusted_schedule = await scheduler.handle_holiday_adjustments(holiday_schedule)
        
        print(f"✅ Holiday adjustment completed:")
        print(f"   Original time: {holiday_schedule.scheduled_time}")
        print(f"   Adjusted time: {adjusted_schedule.scheduled_time}")
        print(f"   Holiday detected: {adjusted_schedule.metadata.get('holiday_detected')}")
        print(f"   Adjustment reason: {adjusted_schedule.metadata.get('adjustment_reason')}")
        
    except Exception as e:
        print(f"❌ Holiday adjustment failed: {e}")


async def main():
    """Run all scheduling demos"""
    print("🚀 Intelligent Scheduler Demo")
    print("=" * 50)
    
    # Run all demos
    await demo_basic_scheduling()
    await demo_timezone_scheduling()
    await demo_retry_logic()
    await demo_manual_trigger()
    await demo_global_coordination()
    await demo_holiday_handling()
    
    print("\n" + "=" * 50)
    print("✅ All demos completed!")


if __name__ == "__main__":
    asyncio.run(main())