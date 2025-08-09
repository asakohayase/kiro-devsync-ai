Create DevSync AI which is a smart release coordination tool that automates communication and coordination tasks within software teams by connecting GitHub, JIRA, and Slack. The tool helps teams stay aligned by generating automatic updates, identifying blockers, and producing weekly changelogs through Kiro’s automation capabilities.

## **What It Does:**

- Tracks GitHub pull requests and summarizes open PRs, merge readiness, and conflict status

- Syncs with JIRA or task boards to monitor ticket progress, detect blockers, and reflect sprint updates

- Sends Slack updates with daily stand-up summaries and real-time development activity

- Generates weekly changelogs based on commit messages, PRs, and issue activity

- Identifies bottlenecks, inactivity, or duplicated efforts within the team

## **Tech Stack:**

- FastAPI (backend service)

- GitHub API (pull request tracking)

- Slack API (message integration)

- JIRA API (sprint tracking and issue sync)

- Supabase (storing summaries and logs)