"""Template modules for different notification types."""

from .pr_templates import (
    PRTemplate,
    NewPRTemplate,
    ReadyForReviewTemplate,
    ApprovedPRTemplate,
    ConflictsTemplate,
    MergedPRTemplate,
    ClosedPRTemplate
)
from .standup_template import StandupTemplate
from .jira_templates import (
    JIRATemplate,
    StatusChangeTemplate,
    PriorityChangeTemplate,
    AssignmentTemplate,
    CommentTemplate,
    BlockerTemplate,
    SprintChangeTemplate
)

__all__ = [
    'PRTemplate',
    'NewPRTemplate',
    'ReadyForReviewTemplate',
    'ApprovedPRTemplate',
    'ConflictsTemplate',
    'MergedPRTemplate',
    'ClosedPRTemplate',
    'StandupTemplate',
    'JIRATemplate',
    'StatusChangeTemplate',
    'PriorityChangeTemplate',
    'AssignmentTemplate',
    'CommentTemplate',
    'BlockerTemplate',
    'SprintChangeTemplate'
]