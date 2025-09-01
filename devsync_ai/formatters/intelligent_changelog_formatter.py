"""
AI-Powered Changelog Formatting Engine

This module provides intelligent changelog formatting with ML-based categorization,
content summarization, dynamic template selection, and multi-format output generation.
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ChangeCategory(Enum):
    """Categories for changelog entries"""
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    IMPROVEMENT = "improvement"
    BREAKING_CHANGE = "breaking_change"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"


class AudienceType(Enum):
    """Target audience types for changelog formatting"""
    TECHNICAL = "technical"
    BUSINESS = "business"
    EXECUTIVE = "executive"
    END_USER = "end_user"
    MIXED = "mixed"


class FormatType(Enum):
    """Output format types"""
    SLACK_BLOCKS = "slack_blocks"
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class ImpactLevel(Enum):
    """Visual impact levels for changes"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ChangeItem:
    """Individual change item with metadata"""
    id: str
    title: str
    description: str
    category: ChangeCategory
    impact_level: ImpactLevel
    confidence_score: float
    author: str
    timestamp: datetime
    pull_request_url: Optional[str] = None
    commit_hash: Optional[str] = None
    breaking_change_details: Optional[Dict[str, Any]] = None
    migration_path: Optional[str] = None
    affected_components: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class CategorizedChanges:
    """Categorized collection of changes"""
    features: List[ChangeItem] = field(default_factory=list)
    bug_fixes: List[ChangeItem] = field(default_factory=list)
    improvements: List[ChangeItem] = field(default_factory=list)
    breaking_changes: List[ChangeItem] = field(default_factory=list)
    security: List[ChangeItem] = field(default_factory=list)
    performance: List[ChangeItem] = field(default_factory=list)
    documentation: List[ChangeItem] = field(default_factory=list)
    refactoring: List[ChangeItem] = field(default_factory=list)
    dependencies: List[ChangeItem] = field(default_factory=list)
    configuration: List[ChangeItem] = field(default_factory=list)

    def get_by_category(self, category: ChangeCategory) -> List[ChangeItem]:
        """Get changes by category"""
        category_map = {
            ChangeCategory.FEATURE: self.features,
            ChangeCategory.BUG_FIX: self.bug_fixes,
            ChangeCategory.IMPROVEMENT: self.improvements,
            ChangeCategory.BREAKING_CHANGE: self.breaking_changes,
            ChangeCategory.SECURITY: self.security,
            ChangeCategory.PERFORMANCE: self.performance,
            ChangeCategory.DOCUMENTATION: self.documentation,
            ChangeCategory.REFACTORING: self.refactoring,
            ChangeCategory.DEPENDENCY: self.dependencies,
            ChangeCategory.CONFIGURATION: self.configuration,
        }
        return category_map.get(category, [])

    def add_change(self, change: ChangeItem) -> None:
        """Add a change to the appropriate category"""
        category_list = self.get_by_category(change.category)
        if category_list is not None:
            category_list.append(change)


@dataclass
class ExecutiveSummary:
    """Executive summary of changes"""
    total_changes: int
    critical_changes: int
    breaking_changes: int
    security_fixes: int
    performance_improvements: int
    key_highlights: List[str]
    business_impact: str
    risk_assessment: str
    recommended_actions: List[str]


@dataclass
class FormattedChangelog:
    """Complete formatted changelog"""
    title: str
    period: str
    executive_summary: ExecutiveSummary
    categorized_changes: CategorizedChanges
    format_type: FormatType
    audience_type: AudienceType
    content: str
    metadata: Dict[str, Any]
    generated_at: datetime


class MLCategorizer:
    """ML-based change categorization engine"""
    
    def __init__(self):
        self.category_patterns = self._load_category_patterns()
        self.breaking_change_patterns = self._load_breaking_change_patterns()
    
    def _load_category_patterns(self) -> Dict[ChangeCategory, List[str]]:
        """Load regex patterns for categorization"""
        return {
            ChangeCategory.FEATURE: [
                r'\b(add|new|implement|introduce|create)\b',
                r'\b(feature|functionality|capability)\b',
                r'\bfeat(\(.*\))?:',
            ],
            ChangeCategory.BUG_FIX: [
                r'\b(fix|resolve|correct|patch|repair)\b',
                r'\b(bug|issue|error|problem|defect)\b',
                r'\bfix(\(.*\))?:',
            ],
            ChangeCategory.IMPROVEMENT: [
                r'\b(improve|enhance|optimize|upgrade|refine)\b',
                r'\b(performance|efficiency|usability)\b',
                r'\bimprove(\(.*\))?:',
            ],
            ChangeCategory.BREAKING_CHANGE: [
                r'\bBREAKING CHANGE\b',
                r'\b(remove|delete|deprecate)\b.*\b(api|interface|method)\b',
                r'\b(major|breaking)\b.*\b(change|update)\b',
            ],
            ChangeCategory.SECURITY: [
                r'\b(security|vulnerability|exploit|cve)\b',
                r'\b(auth|authentication|authorization)\b',
                r'\bsec(\(.*\))?:',
            ],
            ChangeCategory.PERFORMANCE: [
                r'\b(performance|speed|optimization|cache)\b',
                r'\b(faster|slower|memory|cpu)\b',
                r'\bperf(\(.*\))?:',
            ],
            ChangeCategory.DOCUMENTATION: [
                r'\b(doc|documentation|readme|guide)\b',
                r'\b(comment|example|tutorial)\b',
                r'\bdocs(\(.*\))?:',
            ],
            ChangeCategory.REFACTORING: [
                r'\b(refactor|restructure|reorganize|cleanup)\b',
                r'\b(code quality|maintainability)\b',
                r'\brefactor(\(.*\))?:',
            ],
            ChangeCategory.DEPENDENCY: [
                r'\b(dependency|package|library|version)\b',
                r'\b(upgrade|downgrade|update).*\b(dependency|package)\b',
                r'\bdeps(\(.*\))?:',
            ],
            ChangeCategory.CONFIGURATION: [
                r'\b(config|configuration|settings|environment)\b',
                r'\b(env|yaml|json|toml)\b.*\b(file|config)\b',
                r'\bconfig(\(.*\))?:',
            ],
        }
    
    def _load_breaking_change_patterns(self) -> List[str]:
        """Load patterns for detecting breaking changes"""
        return [
            r'\bBREAKING CHANGE\b',
            r'\b(remove|delete)\b.*\b(method|function|class|api)\b',
            r'\b(change|modify)\b.*\b(signature|interface|contract)\b',
            r'\b(deprecate|obsolete)\b',
            r'\bmajor version\b',
            r'\bincompatible\b.*\b(change|update)\b',
        ]
    
    async def categorize_change(self, title: str, description: str) -> Tuple[ChangeCategory, float]:
        """Categorize a change with confidence score"""
        text = f"{title} {description}".lower()
        
        category_scores = {}
        
        for category, patterns in self.category_patterns.items():
            score = 0.0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * 0.3
            
            # Boost score for conventional commit format
            if re.search(rf'\b{category.value}(\(.*\))?:', text):
                score += 0.5
            
            category_scores[category] = min(score, 1.0)
        
        # Find the category with highest score
        if not category_scores or max(category_scores.values()) < 0.1:
            return ChangeCategory.IMPROVEMENT, 0.1
        
        best_category = max(category_scores, key=category_scores.get)
        confidence = category_scores[best_category]
        
        return best_category, confidence
    
    async def detect_breaking_change(self, title: str, description: str) -> Tuple[bool, Optional[str]]:
        """Detect if a change is breaking and provide migration guidance"""
        text = f"{title} {description}".lower()
        
        for pattern in self.breaking_change_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                migration_path = self._generate_migration_guidance(text, pattern)
                return True, migration_path
        
        return False, None
    
    def _generate_migration_guidance(self, text: str, matched_pattern: str) -> str:
        """Generate basic migration guidance based on detected breaking change"""
        if "remove" in matched_pattern or "delete" in matched_pattern:
            return "This change removes functionality. Please update your code to use alternative methods."
        elif "change" in matched_pattern or "modify" in matched_pattern:
            return "This change modifies existing interfaces. Please review and update your integration code."
        elif "deprecate" in matched_pattern:
            return "This functionality is deprecated. Please migrate to the recommended alternative."
        else:
            return "This is a breaking change. Please review the documentation for migration steps."


class ContentSummarizer:
    """NLP-based content summarization engine"""
    
    async def summarize_commit_message(self, message: str, max_length: int = 100) -> str:
        """Summarize a commit message"""
        if len(message) <= max_length:
            return message
        
        # Extract the first line (conventional commit title)
        lines = message.split('\n')
        title = lines[0].strip()
        
        if len(title) <= max_length:
            return title
        
        # Truncate and add ellipsis
        return title[:max_length-3] + "..."
    
    async def summarize_pr_description(self, description: str, max_length: int = 200) -> str:
        """Summarize a PR description"""
        if not description or len(description) <= max_length:
            return description or ""
        
        # Extract key sentences
        sentences = re.split(r'[.!?]+', description)
        summary_sentences = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_length + len(sentence) + 2 <= max_length:
                summary_sentences.append(sentence)
                current_length += len(sentence) + 2
            else:
                break
        
        if summary_sentences:
            return '. '.join(summary_sentences) + '.'
        else:
            return description[:max_length-3] + "..."
    
    async def generate_executive_summary(self, changes: CategorizedChanges) -> ExecutiveSummary:
        """Generate executive summary from categorized changes"""
        total_changes = sum(len(getattr(changes, attr)) for attr in changes.__dataclass_fields__)
        
        critical_changes = sum(
            1 for change_list in [
                changes.breaking_changes,
                changes.security,
                changes.performance
            ]
            for change in change_list
            if change.impact_level in [ImpactLevel.CRITICAL, ImpactLevel.HIGH]
        )
        
        key_highlights = []
        
        # Add feature highlights
        if changes.features:
            feature_count = len(changes.features)
            key_highlights.append(f"{feature_count} new feature{'s' if feature_count > 1 else ''} added")
        
        # Add security highlights
        if changes.security:
            security_count = len(changes.security)
            key_highlights.append(f"{security_count} security fix{'es' if security_count > 1 else ''} applied")
        
        # Add performance highlights
        if changes.performance:
            perf_count = len(changes.performance)
            key_highlights.append(f"{perf_count} performance improvement{'s' if perf_count > 1 else ''}")
        
        # Generate business impact assessment
        business_impact = self._assess_business_impact(changes)
        risk_assessment = self._assess_risk(changes)
        recommended_actions = self._generate_recommendations(changes)
        
        return ExecutiveSummary(
            total_changes=total_changes,
            critical_changes=critical_changes,
            breaking_changes=len(changes.breaking_changes),
            security_fixes=len(changes.security),
            performance_improvements=len(changes.performance),
            key_highlights=key_highlights,
            business_impact=business_impact,
            risk_assessment=risk_assessment,
            recommended_actions=recommended_actions
        )
    
    def _assess_business_impact(self, changes: CategorizedChanges) -> str:
        """Assess business impact of changes"""
        if changes.breaking_changes:
            return "High - Breaking changes may impact existing integrations"
        elif changes.security:
            return "Medium-High - Security improvements enhance system reliability"
        elif changes.features:
            return "Medium - New features provide additional value to users"
        else:
            return "Low - Maintenance and improvement changes"
    
    def _assess_risk(self, changes: CategorizedChanges) -> str:
        """Assess deployment risk"""
        risk_factors = []
        
        if changes.breaking_changes:
            risk_factors.append("breaking changes")
        if len(changes.features) > 5:
            risk_factors.append("multiple new features")
        if any(change.impact_level == ImpactLevel.CRITICAL for change_list in 
               [changes.features, changes.improvements, changes.bug_fixes] 
               for change in change_list):
            risk_factors.append("critical system changes")
        
        if not risk_factors:
            return "Low risk deployment"
        elif len(risk_factors) == 1:
            return f"Medium risk due to {risk_factors[0]}"
        else:
            return f"High risk due to {', '.join(risk_factors)}"
    
    def _generate_recommendations(self, changes: CategorizedChanges) -> List[str]:
        """Generate recommended actions"""
        recommendations = []
        
        if changes.breaking_changes:
            recommendations.append("Review breaking changes and update integration documentation")
            recommendations.append("Coordinate with dependent teams before deployment")
        
        if changes.security:
            recommendations.append("Prioritize security fixes in deployment schedule")
        
        if len(changes.features) > 3:
            recommendations.append("Consider phased rollout for multiple new features")
        
        if not recommendations:
            recommendations.append("Standard deployment process recommended")
        
        return recommendations


class TemplateSelector:
    """Dynamic template selection based on content and audience"""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load template configurations"""
        return {
            "technical_detailed": {
                "audience": AudienceType.TECHNICAL,
                "sections": ["breaking_changes", "features", "bug_fixes", "improvements", 
                           "performance", "security", "refactoring", "dependencies"],
                "include_technical_details": True,
                "include_code_examples": True,
                "include_migration_paths": True,
            },
            "business_summary": {
                "audience": AudienceType.BUSINESS,
                "sections": ["executive_summary", "features", "bug_fixes", "security"],
                "include_technical_details": False,
                "include_business_impact": True,
                "include_user_benefits": True,
            },
            "executive_brief": {
                "audience": AudienceType.EXECUTIVE,
                "sections": ["executive_summary", "key_metrics", "risk_assessment"],
                "include_technical_details": False,
                "include_high_level_metrics": True,
                "include_strategic_impact": True,
            },
            "end_user_friendly": {
                "audience": AudienceType.END_USER,
                "sections": ["features", "improvements", "bug_fixes"],
                "include_technical_details": False,
                "include_user_benefits": True,
                "use_friendly_language": True,
            },
        }
    
    async def select_template(self, changes: CategorizedChanges, audience: AudienceType) -> Dict[str, Any]:
        """Select appropriate template based on content and audience"""
        # Map audience to template
        template_map = {
            AudienceType.TECHNICAL: "technical_detailed",
            AudienceType.BUSINESS: "business_summary",
            AudienceType.EXECUTIVE: "executive_brief",
            AudienceType.END_USER: "end_user_friendly",
            AudienceType.MIXED: "business_summary",  # Default for mixed audience
        }
        
        template_name = template_map.get(audience, "business_summary")
        template = self.templates[template_name].copy()
        
        # Adjust template based on content
        if changes.breaking_changes and "breaking_changes" not in template["sections"]:
            template["sections"].insert(0, "breaking_changes")
        
        if changes.security and audience != AudienceType.END_USER:
            if "security" not in template["sections"]:
                template["sections"].insert(-1, "security")
        
        return template


class IntelligentChangelogFormatter:
    """
    AI-Powered Changelog Formatting Engine
    
    Provides intelligent changelog formatting with ML-based categorization,
    content summarization, dynamic template selection, and multi-format output.
    """
    
    def __init__(self):
        self.categorizer = MLCategorizer()
        self.summarizer = ContentSummarizer()
        self.template_selector = TemplateSelector()
        self.impact_scorer = ImpactScorer()
    
    async def format_changelog(
        self,
        changes: List[Dict[str, Any]],
        audience: AudienceType = AudienceType.MIXED,
        format_type: FormatType = FormatType.MARKDOWN,
        period: str = "This Week"
    ) -> FormattedChangelog:
        """
        Format a complete changelog with intelligent processing
        
        Args:
            changes: List of raw change data
            audience: Target audience type
            format_type: Output format type
            period: Time period description
            
        Returns:
            FormattedChangelog: Complete formatted changelog
        """
        logger.info(f"Formatting changelog for {len(changes)} changes, audience: {audience.value}")
        
        # Process and categorize changes
        categorized_changes = await self._process_changes(changes)
        
        # Generate executive summary
        executive_summary = await self.summarizer.generate_executive_summary(categorized_changes)
        
        # Select appropriate template
        template = await self.template_selector.select_template(categorized_changes, audience)
        
        # Generate formatted content
        content = await self._generate_content(
            categorized_changes, executive_summary, template, format_type
        )
        
        # Create formatted changelog
        changelog = FormattedChangelog(
            title=f"Changelog - {period}",
            period=period,
            executive_summary=executive_summary,
            categorized_changes=categorized_changes,
            format_type=format_type,
            audience_type=audience,
            content=content,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "total_changes": executive_summary.total_changes,
                "template_used": template,
                "processing_stats": {
                    "categorization_confidence": self._calculate_avg_confidence(categorized_changes),
                    "breaking_changes_detected": len(categorized_changes.breaking_changes),
                    "high_impact_changes": self._count_high_impact_changes(categorized_changes),
                }
            },
            generated_at=datetime.now()
        )
        
        logger.info(f"Changelog formatted successfully: {executive_summary.total_changes} changes processed")
        return changelog    

    async def _process_changes(self, raw_changes: List[Dict[str, Any]]) -> CategorizedChanges:
        """Process and categorize raw changes"""
        categorized = CategorizedChanges()
        
        for raw_change in raw_changes:
            try:
                change_item = await self._create_change_item(raw_change)
                categorized.add_change(change_item)
            except Exception as e:
                logger.warning(f"Failed to process change {raw_change.get('id', 'unknown')}: {e}")
                continue
        
        return categorized
    
    async def _create_change_item(self, raw_change: Dict[str, Any]) -> ChangeItem:
        """Create a ChangeItem from raw change data"""
        title = raw_change.get('title', '')
        description = raw_change.get('description', '')
        
        # Categorize the change
        category, confidence = await self.categorizer.categorize_change(title, description)
        
        # Detect breaking changes
        is_breaking, migration_path = await self.categorizer.detect_breaking_change(title, description)
        if is_breaking:
            category = ChangeCategory.BREAKING_CHANGE
        
        # Calculate impact level
        impact_level = await self.impact_scorer.calculate_impact_level(raw_change)
        
        # Summarize content
        summarized_title = await self.summarizer.summarize_commit_message(title, 80)
        summarized_description = await self.summarizer.summarize_pr_description(description, 150)
        
        return ChangeItem(
            id=raw_change.get('id', ''),
            title=summarized_title,
            description=summarized_description,
            category=category,
            impact_level=impact_level,
            confidence_score=confidence,
            author=raw_change.get('author', ''),
            timestamp=datetime.fromisoformat(raw_change.get('timestamp', datetime.now().isoformat())),
            pull_request_url=raw_change.get('pull_request_url'),
            commit_hash=raw_change.get('commit_hash'),
            breaking_change_details=raw_change.get('breaking_change_details') if is_breaking else None,
            migration_path=migration_path,
            affected_components=raw_change.get('affected_components', []),
            tags=raw_change.get('tags', [])
        )
    
    async def _generate_content(
        self,
        changes: CategorizedChanges,
        summary: ExecutiveSummary,
        template: Dict[str, Any],
        format_type: FormatType
    ) -> str:
        """Generate formatted content based on template and format"""
        if format_type == FormatType.SLACK_BLOCKS:
            return await self._generate_slack_blocks(changes, summary, template)
        elif format_type == FormatType.HTML:
            return await self._generate_html(changes, summary, template)
        elif format_type == FormatType.PDF:
            return await self._generate_pdf_content(changes, summary, template)
        elif format_type == FormatType.MARKDOWN:
            return await self._generate_markdown(changes, summary, template)
        else:
            return await self._generate_plain_text(changes, summary, template)
    
    async def _generate_markdown(
        self,
        changes: CategorizedChanges,
        summary: ExecutiveSummary,
        template: Dict[str, Any]
    ) -> str:
        """Generate Markdown formatted changelog"""
        content = []
        
        # Title and metadata
        content.append("# Weekly Development Changelog")
        content.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # Executive Summary
        if "executive_summary" in template["sections"]:
            content.append("## 📊 Executive Summary")
            content.append(f"- **Total Changes**: {summary.total_changes}")
            content.append(f"- **Critical Changes**: {summary.critical_changes}")
            content.append(f"- **Breaking Changes**: {summary.breaking_changes}")
            content.append(f"- **Security Fixes**: {summary.security_fixes}")
            content.append(f"- **Performance Improvements**: {summary.performance_improvements}")
            
            if summary.key_highlights:
                content.append("\n### Key Highlights")
                for highlight in summary.key_highlights:
                    content.append(f"- {highlight}")
            
            content.append(f"\n**Business Impact**: {summary.business_impact}")
            content.append(f"**Risk Assessment**: {summary.risk_assessment}")
            
            if summary.recommended_actions:
                content.append("\n### Recommended Actions")
                for action in summary.recommended_actions:
                    content.append(f"- {action}")
            content.append("")
        
        # Breaking Changes (always first if present)
        if changes.breaking_changes and "breaking_changes" in template["sections"]:
            content.append("## 🚨 Breaking Changes")
            for change in changes.breaking_changes:
                content.append(f"### {change.title}")
                if change.description:
                    content.append(f"{change.description}")
                if change.migration_path:
                    content.append(f"**Migration Path**: {change.migration_path}")
                if change.pull_request_url:
                    content.append(f"[View PR]({change.pull_request_url})")
                content.append("")
        
        # Other sections
        section_map = {
            "features": ("✨ New Features", changes.features),
            "bug_fixes": ("🐛 Bug Fixes", changes.bug_fixes),
            "improvements": ("⚡ Improvements", changes.improvements),
            "security": ("🔒 Security", changes.security),
            "performance": ("🚀 Performance", changes.performance),
            "documentation": ("📚 Documentation", changes.documentation),
            "refactoring": ("♻️ Refactoring", changes.refactoring),
            "dependencies": ("📦 Dependencies", changes.dependencies),
            "configuration": ("⚙️ Configuration", changes.configuration),
        }
        
        for section_key in template["sections"]:
            if section_key in section_map:
                section_title, section_changes = section_map[section_key]
                if section_changes:
                    content.append(f"## {section_title}")
                    for change in section_changes:
                        impact_emoji = self._get_impact_emoji(change.impact_level)
                        content.append(f"- {impact_emoji} **{change.title}**")
                        if template.get("include_technical_details", False) and change.description:
                            content.append(f"  {change.description}")
                        if change.author:
                            content.append(f"  *by {change.author}*")
                        if change.pull_request_url:
                            content.append(f"  [View PR]({change.pull_request_url})")
                    content.append("")
        
        return "\n".join(content)
    
    async def _generate_slack_blocks(
        self,
        changes: CategorizedChanges,
        summary: ExecutiveSummary,
        template: Dict[str, Any]
    ) -> str:
        """Generate Slack Block Kit formatted changelog"""
        blocks = []
        
        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📋 Weekly Development Changelog"
            }
        })
        
        # Executive Summary
        if "executive_summary" in template["sections"]:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Executive Summary*\n"
                           f"• Total Changes: *{summary.total_changes}*\n"
                           f"• Critical Changes: *{summary.critical_changes}*\n"
                           f"• Breaking Changes: *{summary.breaking_changes}*\n"
                           f"• Security Fixes: *{summary.security_fixes}*"
                }
            })
            
            if summary.key_highlights:
                highlights_text = "\n".join([f"• {h}" for h in summary.key_highlights])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Key Highlights*\n{highlights_text}"
                    }
                })
        
        # Breaking Changes
        if changes.breaking_changes:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🚨 Breaking Changes*"
                }
            })
            
            for change in changes.breaking_changes[:3]:  # Limit for Slack
                change_text = f"*{change.title}*"
                if change.migration_path:
                    change_text += f"\n_Migration: {change.migration_path}_"
                
                block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": change_text
                    }
                }
                
                if change.pull_request_url:
                    block["accessory"] = {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View PR"
                        },
                        "url": change.pull_request_url
                    }
                
                blocks.append(block)
        
        # Other sections (condensed for Slack)
        section_emojis = {
            "features": "✨",
            "bug_fixes": "🐛",
            "improvements": "⚡",
            "security": "🔒",
            "performance": "🚀"
        }
        
        for section_key in ["features", "bug_fixes", "improvements", "security", "performance"]:
            if section_key in template["sections"]:
                section_changes = getattr(changes, section_key)
                if section_changes:
                    emoji = section_emojis.get(section_key, "•")
                    section_title = section_key.replace("_", " ").title()
                    
                    change_list = []
                    for change in section_changes[:5]:  # Limit for readability
                        impact_emoji = self._get_impact_emoji(change.impact_level)
                        change_list.append(f"{impact_emoji} {change.title}")
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{emoji} {section_title}*\n" + "\n".join(change_list)
                        }
                    })
        
        return json.dumps(blocks, indent=2)
    
    async def _generate_html(
        self,
        changes: CategorizedChanges,
        summary: ExecutiveSummary,
        template: Dict[str, Any]
    ) -> str:
        """Generate HTML formatted changelog"""
        html_parts = []
        
        # HTML header
        html_parts.append("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Development Changelog</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
        .summary { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .section h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .change-item { background: white; border: 1px solid #e1e8ed; border-radius: 6px; 
                       padding: 15px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .change-title { font-weight: 600; color: #1a1a1a; margin-bottom: 8px; }
        .change-meta { color: #657786; font-size: 0.9em; }
        .impact-critical { border-left: 4px solid #e74c3c; }
        .impact-high { border-left: 4px solid #f39c12; }
        .impact-medium { border-left: 4px solid #3498db; }
        .impact-low { border-left: 4px solid #2ecc71; }
        .breaking-change { background: #fff5f5; border-color: #e74c3c; }
        .migration-path { background: #fff3cd; padding: 10px; border-radius: 4px; margin-top: 10px; }
    </style>
</head>
<body>
""")
        
        # Header
        html_parts.append(f"""
    <div class="header">
        <h1>📋 Weekly Development Changelog</h1>
        <p>Generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
    </div>
""")
        
        # Executive Summary
        if "executive_summary" in template["sections"]:
            html_parts.append(f"""
    <div class="summary">
        <h2>📊 Executive Summary</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
            <div><strong>Total Changes:</strong> {summary.total_changes}</div>
            <div><strong>Critical Changes:</strong> {summary.critical_changes}</div>
            <div><strong>Breaking Changes:</strong> {summary.breaking_changes}</div>
            <div><strong>Security Fixes:</strong> {summary.security_fixes}</div>
        </div>
        
        {f'<h3>Key Highlights</h3><ul>{"".join([f"<li>{h}</li>" for h in summary.key_highlights])}</ul>' if summary.key_highlights else ''}
        
        <p><strong>Business Impact:</strong> {summary.business_impact}</p>
        <p><strong>Risk Assessment:</strong> {summary.risk_assessment}</p>
        
        {f'<h3>Recommended Actions</h3><ul>{"".join([f"<li>{a}</li>" for a in summary.recommended_actions])}</ul>' if summary.recommended_actions else ''}
    </div>
""")
        
        # Breaking Changes
        if changes.breaking_changes:
            html_parts.append('<div class="section"><h2>🚨 Breaking Changes</h2>')
            for change in changes.breaking_changes:
                html_parts.append(f"""
    <div class="change-item breaking-change impact-{change.impact_level.value}">
        <div class="change-title">{change.title}</div>
        {f'<p>{change.description}</p>' if change.description else ''}
        {f'<div class="migration-path"><strong>Migration Path:</strong> {change.migration_path}</div>' if change.migration_path else ''}
        <div class="change-meta">
            By {change.author} • {change.timestamp.strftime('%Y-%m-%d')}
            {f' • <a href="{change.pull_request_url}" target="_blank">View PR</a>' if change.pull_request_url else ''}
        </div>
    </div>
""")
            html_parts.append('</div>')
        
        # Other sections
        section_map = {
            "features": ("✨ New Features", changes.features),
            "bug_fixes": ("🐛 Bug Fixes", changes.bug_fixes),
            "improvements": ("⚡ Improvements", changes.improvements),
            "security": ("🔒 Security", changes.security),
            "performance": ("🚀 Performance", changes.performance),
        }
        
        for section_key in template["sections"]:
            if section_key in section_map:
                section_title, section_changes = section_map[section_key]
                if section_changes:
                    html_parts.append(f'<div class="section"><h2>{section_title}</h2>')
                    for change in section_changes:
                        html_parts.append(f"""
    <div class="change-item impact-{change.impact_level.value}">
        <div class="change-title">{change.title}</div>
        {f'<p>{change.description}</p>' if template.get("include_technical_details", False) and change.description else ''}
        <div class="change-meta">
            By {change.author} • {change.timestamp.strftime('%Y-%m-%d')}
            {f' • <a href="{change.pull_request_url}" target="_blank">View PR</a>' if change.pull_request_url else ''}
        </div>
    </div>
""")
                    html_parts.append('</div>')
        
        # HTML footer
        html_parts.append("""
</body>
</html>
""")
        
        return "".join(html_parts)
    
    async def _generate_pdf_content(
        self,
        changes: CategorizedChanges,
        summary: ExecutiveSummary,
        template: Dict[str, Any]
    ) -> str:
        """Generate PDF-ready HTML content"""
        # For PDF generation, we create a simplified HTML version
        # that's optimized for PDF rendering
        html_content = await self._generate_html(changes, summary, template)
        
        # Add PDF-specific styles
        pdf_styles = """
        <style>
            @media print {
                body { font-size: 12pt; }
                .header { background: #667eea !important; -webkit-print-color-adjust: exact; }
                .change-item { page-break-inside: avoid; }
                .section { page-break-before: auto; }
            }
        </style>
        """
        
        # Insert PDF styles before closing head tag
        html_content = html_content.replace("</head>", f"{pdf_styles}</head>")
        
        return html_content
    
    async def _generate_plain_text(
        self,
        changes: CategorizedChanges,
        summary: ExecutiveSummary,
        template: Dict[str, Any]
    ) -> str:
        """Generate plain text formatted changelog"""
        content = []
        
        # Header
        content.append("=" * 60)
        content.append("WEEKLY DEVELOPMENT CHANGELOG")
        content.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append("=" * 60)
        content.append("")
        
        # Executive Summary
        if "executive_summary" in template["sections"]:
            content.append("EXECUTIVE SUMMARY")
            content.append("-" * 20)
            content.append(f"Total Changes: {summary.total_changes}")
            content.append(f"Critical Changes: {summary.critical_changes}")
            content.append(f"Breaking Changes: {summary.breaking_changes}")
            content.append(f"Security Fixes: {summary.security_fixes}")
            content.append(f"Performance Improvements: {summary.performance_improvements}")
            content.append("")
            
            if summary.key_highlights:
                content.append("Key Highlights:")
                for highlight in summary.key_highlights:
                    content.append(f"  - {highlight}")
                content.append("")
            
            content.append(f"Business Impact: {summary.business_impact}")
            content.append(f"Risk Assessment: {summary.risk_assessment}")
            content.append("")
        
        # Breaking Changes
        if changes.breaking_changes:
            content.append("BREAKING CHANGES")
            content.append("-" * 20)
            for change in changes.breaking_changes:
                content.append(f"* {change.title}")
                if change.description:
                    content.append(f"  {change.description}")
                if change.migration_path:
                    content.append(f"  Migration: {change.migration_path}")
                content.append(f"  By: {change.author}")
                content.append("")
        
        # Other sections
        section_map = {
            "features": ("NEW FEATURES", changes.features),
            "bug_fixes": ("BUG FIXES", changes.bug_fixes),
            "improvements": ("IMPROVEMENTS", changes.improvements),
            "security": ("SECURITY", changes.security),
            "performance": ("PERFORMANCE", changes.performance),
        }
        
        for section_key in template["sections"]:
            if section_key in section_map:
                section_title, section_changes = section_map[section_key]
                if section_changes:
                    content.append(section_title)
                    content.append("-" * len(section_title))
                    for change in section_changes:
                        impact_indicator = self._get_impact_indicator(change.impact_level)
                        content.append(f"{impact_indicator} {change.title}")
                        if template.get("include_technical_details", False) and change.description:
                            content.append(f"  {change.description}")
                        content.append(f"  By: {change.author}")
                    content.append("")
        
        return "\n".join(content)
    
    def _get_impact_emoji(self, impact_level: ImpactLevel) -> str:
        """Get emoji for impact level"""
        emoji_map = {
            ImpactLevel.CRITICAL: "🔴",
            ImpactLevel.HIGH: "🟡",
            ImpactLevel.MEDIUM: "🔵",
            ImpactLevel.LOW: "⚪",
        }
        return emoji_map.get(impact_level, "⚪")
    
    def _get_impact_indicator(self, impact_level: ImpactLevel) -> str:
        """Get text indicator for impact level"""
        indicator_map = {
            ImpactLevel.CRITICAL: "[CRITICAL]",
            ImpactLevel.HIGH: "[HIGH]",
            ImpactLevel.MEDIUM: "[MEDIUM]",
            ImpactLevel.LOW: "[LOW]",
        }
        return indicator_map.get(impact_level, "[LOW]")
    
    def _calculate_avg_confidence(self, changes: CategorizedChanges) -> float:
        """Calculate average categorization confidence"""
        all_changes = []
        for attr in changes.__dataclass_fields__:
            all_changes.extend(getattr(changes, attr))
        
        if not all_changes:
            return 0.0
        
        total_confidence = sum(change.confidence_score for change in all_changes)
        return total_confidence / len(all_changes)
    
    def _count_high_impact_changes(self, changes: CategorizedChanges) -> int:
        """Count high impact changes"""
        count = 0
        for attr in changes.__dataclass_fields__:
            change_list = getattr(changes, attr)
            count += sum(1 for change in change_list 
                        if change.impact_level in [ImpactLevel.CRITICAL, ImpactLevel.HIGH])
        return count


class ImpactScorer:
    """Visual impact scoring and automated priority ranking"""
    
    async def calculate_impact_level(self, change_data: Dict[str, Any]) -> ImpactLevel:
        """Calculate impact level based on change characteristics"""
        score = 0.0
        
        # File change analysis
        files_changed = change_data.get('files_changed', 0)
        if files_changed > 20:
            score += 0.4
        elif files_changed > 10:
            score += 0.3
        elif files_changed > 5:
            score += 0.2
        else:
            score += 0.1
        
        # Lines changed analysis
        lines_added = change_data.get('lines_added', 0)
        lines_deleted = change_data.get('lines_deleted', 0)
        total_lines = lines_added + lines_deleted
        
        if total_lines > 1000:
            score += 0.4
        elif total_lines > 500:
            score += 0.3
        elif total_lines > 100:
            score += 0.2
        else:
            score += 0.1
        
        # Component impact
        affected_components = change_data.get('affected_components', [])
        critical_components = ['auth', 'security', 'database', 'api', 'core']
        
        if any(comp in critical_components for comp in affected_components):
            score += 0.3
        
        # Test coverage impact
        test_coverage_change = change_data.get('test_coverage_change', 0)
        if test_coverage_change < -5:  # Significant coverage decrease
            score += 0.2
        elif test_coverage_change > 10:  # Significant coverage increase
            score += 0.1
        
        # Review complexity
        review_comments = change_data.get('review_comments', 0)
        if review_comments > 20:
            score += 0.2
        elif review_comments > 10:
            score += 0.1
        
        # Map score to impact level
        if score >= 0.8:
            return ImpactLevel.CRITICAL
        elif score >= 0.6:
            return ImpactLevel.HIGH
        elif score >= 0.4:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW


# Export main class
__all__ = ['IntelligentChangelogFormatter', 'ChangeCategory', 'AudienceType', 'FormatType', 'ImpactLevel']