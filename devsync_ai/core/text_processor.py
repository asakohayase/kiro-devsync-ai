"""Text processing utilities for enhanced formatting and content detection."""

import re
import html
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib


class ContentType(Enum):
    """Types of detected content."""
    GITHUB_ISSUE = "github_issue"
    GITHUB_PR = "github_pr"
    JIRA_TICKET = "jira_ticket"
    COMMIT_HASH = "commit_hash"
    USER_MENTION = "user_mention"
    URL = "url"
    EMAIL = "email"
    CODE_BLOCK = "code_block"
    INLINE_CODE = "inline_code"


@dataclass
class ProcessingConfig:
    """Configuration for text processing."""
    github_repo: Optional[str] = None
    jira_base_url: Optional[str] = None
    max_length: int = 500
    truncation_strategy: str = "smart"  # smart, word, character
    enable_auto_linking: bool = True
    enable_markdown_conversion: bool = True
    enable_code_highlighting: bool = True
    sanitize_html: bool = True
    preserve_formatting: bool = True
    show_more_threshold: int = 300


@dataclass
class DetectedContent:
    """Represents detected content in text."""
    content_type: ContentType
    original_text: str
    replacement_text: str
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of text processing."""
    processed_text: str
    original_text: str
    detected_content: List[DetectedContent] = field(default_factory=list)
    truncated: bool = False
    show_more_available: bool = False
    word_count: int = 0
    processing_time_ms: float = 0.0


class TextProcessor:
    """Advanced text processor for Slack message formatting."""
    
    # Regex patterns for content detection
    PATTERNS = {
        # GitHub issues and PRs
        'github_issue': re.compile(r'#(\d+)(?!\d)', re.IGNORECASE),
        'github_pr': re.compile(r'(?:PR|pull request)\s*#(\d+)', re.IGNORECASE),
        
        # JIRA tickets
        'jira_ticket': re.compile(r'\b([A-Z][A-Z0-9]+-\d+)\b'),
        
        # Commit hashes (7-40 characters)
        'commit_hash': re.compile(r'\b([a-f0-9]{7,40})\b', re.IGNORECASE),
        
        # User mentions
        'user_mention': re.compile(r'@([a-zA-Z0-9._-]+)'),
        
        # URLs
        'url': re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
        
        # Email addresses
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        
        # Markdown patterns
        'bold': re.compile(r'\*\*(.*?)\*\*'),
        'italic': re.compile(r'\*(.*?)\*'),
        'code': re.compile(r'`([^`]+)`'),
        'link': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
        'code_block': re.compile(r'```(\w+)?\n?(.*?)```', re.DOTALL),
        
        # Lists
        'bullet_list': re.compile(r'^[\s]*[-*+]\s+(.+)$', re.MULTILINE),
        'numbered_list': re.compile(r'^[\s]*\d+\.\s+(.+)$', re.MULTILINE),
    }
    
    # Language detection for code blocks
    LANGUAGE_KEYWORDS = {
        'python': ['def ', 'import ', 'from ', 'class ', 'if __name__'],
        'javascript': ['function ', 'const ', 'let ', 'var ', '=>', 'console.log'],
        'typescript': ['interface ', 'type ', 'export ', 'import ', '=>'],
        'java': ['public class', 'private ', 'public ', 'import java'],
        'go': ['func ', 'package ', 'import ', 'var ', 'type '],
        'rust': ['fn ', 'let ', 'mut ', 'use ', 'struct '],
        'sql': ['SELECT ', 'FROM ', 'WHERE ', 'INSERT ', 'UPDATE'],
        'bash': ['#!/bin/bash', 'echo ', 'export ', 'if [', 'for '],
        'yaml': ['---', 'version:', 'name:', 'on:', 'jobs:'],
        'json': ['{', '}', '":', '": "', '"": '],
        'html': ['<html', '<div', '<span', '<!DOCTYPE'],
        'css': ['{', '}', ':', ';', 'px', 'color:'],
    }
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize text processor with configuration."""
        self.config = config or ProcessingConfig()
        
        # Compile patterns for performance
        self._compiled_patterns = {
            name: pattern for name, pattern in self.PATTERNS.items()
        }
    
    def process_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """Process text with all enhancements."""
        if not text:
            return ProcessingResult(processed_text="", original_text="")
        
        import time
        start_time = time.time()
        
        original_text = text
        processed_text = text
        detected_content = []
        
        # Step 1: Sanitize HTML if enabled
        if self.config.sanitize_html:
            processed_text = html.escape(processed_text)
        
        # Step 2: Detect and process content
        if self.config.enable_auto_linking:
            processed_text, content_detections = self._detect_and_link_content(processed_text, context)
            detected_content.extend(content_detections)
        
        # Step 3: Convert markdown to Slack formatting
        if self.config.enable_markdown_conversion:
            processed_text = self._convert_markdown_to_slack(processed_text)
        
        # Step 4: Handle truncation
        truncated = False
        show_more_available = False
        if len(processed_text) > self.config.max_length:
            processed_text, truncated, show_more_available = self._smart_truncate(
                processed_text, self.config.max_length
            )
        
        # Step 5: Calculate metrics
        word_count = len(processed_text.split())
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResult(
            processed_text=processed_text,
            original_text=original_text,
            detected_content=detected_content,
            truncated=truncated,
            show_more_available=show_more_available,
            word_count=word_count,
            processing_time_ms=processing_time
        )
    
    def _detect_and_link_content(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[DetectedContent]]:
        """Detect and auto-link various content types."""
        detected_content = []
        processed_text = text
        
        # GitHub issues and PRs
        if self.config.github_repo:
            processed_text, github_detections = self._process_github_references(processed_text)
            detected_content.extend(github_detections)
        
        # JIRA tickets
        if self.config.jira_base_url:
            processed_text, jira_detections = self._process_jira_tickets(processed_text)
            detected_content.extend(jira_detections)
        
        # Commit hashes
        if self.config.github_repo:
            processed_text, commit_detections = self._process_commit_hashes(processed_text)
            detected_content.extend(commit_detections)
        
        # User mentions
        processed_text, mention_detections = self._process_user_mentions(processed_text)
        detected_content.extend(mention_detections)
        
        # URLs (process last to avoid conflicts)
        processed_text, url_detections = self._process_urls(processed_text)
        detected_content.extend(url_detections)
        
        return processed_text, detected_content
    
    def _process_github_references(self, text: str) -> Tuple[str, List[DetectedContent]]:
        """Process GitHub issue and PR references."""
        detected_content = []
        
        # GitHub issues (#123)
        def replace_issue(match):
            issue_num = match.group(1)
            url = f"https://github.com/{self.config.github_repo}/issues/{issue_num}"
            link_text = f"<{url}|#{issue_num}>"
            
            detected_content.append(DetectedContent(
                content_type=ContentType.GITHUB_ISSUE,
                original_text=match.group(0),
                replacement_text=link_text,
                url=url,
                metadata={'issue_number': issue_num}
            ))
            return link_text
        
        text = self.PATTERNS['github_issue'].sub(replace_issue, text)
        
        # GitHub PRs (PR #456)
        def replace_pr(match):
            pr_num = match.group(1)
            url = f"https://github.com/{self.config.github_repo}/pull/{pr_num}"
            link_text = f"<{url}|PR #{pr_num}>"
            
            detected_content.append(DetectedContent(
                content_type=ContentType.GITHUB_PR,
                original_text=match.group(0),
                replacement_text=link_text,
                url=url,
                metadata={'pr_number': pr_num}
            ))
            return link_text
        
        text = self.PATTERNS['github_pr'].sub(replace_pr, text)
        
        return text, detected_content
    
    def _process_jira_tickets(self, text: str) -> Tuple[str, List[DetectedContent]]:
        """Process JIRA ticket references."""
        detected_content = []
        
        def replace_jira(match):
            ticket_key = match.group(1)
            url = f"{self.config.jira_base_url}/browse/{ticket_key}"
            link_text = f"<{url}|{ticket_key}>"
            
            detected_content.append(DetectedContent(
                content_type=ContentType.JIRA_TICKET,
                original_text=match.group(0),
                replacement_text=link_text,
                url=url,
                metadata={'ticket_key': ticket_key}
            ))
            return link_text
        
        text = self.PATTERNS['jira_ticket'].sub(replace_jira, text)
        return text, detected_content
    
    def _process_commit_hashes(self, text: str) -> Tuple[str, List[DetectedContent]]:
        """Process commit hash references."""
        detected_content = []
        
        def replace_commit(match):
            commit_hash = match.group(1)
            # Only process if it looks like a real commit hash (7+ chars, hex)
            if len(commit_hash) >= 7 and all(c in '0123456789abcdefABCDEF' for c in commit_hash):
                url = f"https://github.com/{self.config.github_repo}/commit/{commit_hash}"
                short_hash = commit_hash[:7]
                link_text = f"<{url}|{short_hash}>"
                
                detected_content.append(DetectedContent(
                    content_type=ContentType.COMMIT_HASH,
                    original_text=match.group(0),
                    replacement_text=link_text,
                    url=url,
                    metadata={'commit_hash': commit_hash, 'short_hash': short_hash}
                ))
                return link_text
            return match.group(0)
        
        text = self.PATTERNS['commit_hash'].sub(replace_commit, text)
        return text, detected_content
    
    def _process_user_mentions(self, text: str) -> Tuple[str, List[DetectedContent]]:
        """Process user mentions."""
        detected_content = []
        
        def replace_mention(match):
            username = match.group(1)
            slack_mention = f"<@{username}>"
            
            detected_content.append(DetectedContent(
                content_type=ContentType.USER_MENTION,
                original_text=match.group(0),
                replacement_text=slack_mention,
                metadata={'username': username}
            ))
            return slack_mention
        
        text = self.PATTERNS['user_mention'].sub(replace_mention, text)
        return text, detected_content
    
    def _process_urls(self, text: str) -> Tuple[str, List[DetectedContent]]:
        """Process URL references."""
        detected_content = []
        
        def replace_url(match):
            url = match.group(0)
            # Create a display name from the URL
            display_name = url.replace('https://', '').replace('http://', '')
            if len(display_name) > 50:
                display_name = display_name[:47] + "..."
            
            link_text = f"<{url}|{display_name}>"
            
            detected_content.append(DetectedContent(
                content_type=ContentType.URL,
                original_text=match.group(0),
                replacement_text=link_text,
                url=url,
                metadata={'display_name': display_name}
            ))
            return link_text
        
        text = self.PATTERNS['url'].sub(replace_url, text)
        return text, detected_content
    
    def _convert_markdown_to_slack(self, text: str) -> str:
        """Convert markdown formatting to Slack formatting."""
        
        # Code blocks (must be processed first)
        def replace_code_block(match):
            language = match.group(1) or ""
            code = match.group(2).strip()
            
            # Detect language if not specified
            if not language:
                language = self._detect_code_language(code)
            
            # Format as Slack code block
            if language:
                return f"```{language}\n{code}\n```"
            else:
                return f"```\n{code}\n```"
        
        text = self.PATTERNS['code_block'].sub(replace_code_block, text)
        
        # Inline code
        text = self.PATTERNS['code'].sub(r'`\1`', text)
        
        # Process bold and italic with temporary placeholders to avoid conflicts
        # First, replace bold with a placeholder
        bold_placeholder = "___BOLD_PLACEHOLDER___"
        bold_matches = []
        
        def replace_bold(match):
            bold_matches.append(match.group(1))
            return f"{bold_placeholder}{len(bold_matches)-1}{bold_placeholder}"
        
        text = self.PATTERNS['bold'].sub(replace_bold, text)
        
        # Then process italic
        text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'_\1_', text)
        
        # Finally, restore bold formatting
        for i, bold_text in enumerate(bold_matches):
            text = text.replace(f"{bold_placeholder}{i}{bold_placeholder}", f"*{bold_text}*")
        
        # Links
        text = self.PATTERNS['link'].sub(r'<\2|\1>', text)
        
        # Process lists
        text = self._convert_lists_to_slack(text)
        
        return text
    
    def _convert_lists_to_slack(self, text: str) -> str:
        """Convert markdown lists to Slack-friendly format."""
        
        # Bullet lists
        def replace_bullet(match):
            return f"• {match.group(1)}"
        
        text = self.PATTERNS['bullet_list'].sub(replace_bullet, text)
        
        # Numbered lists (keep as is, Slack handles them well)
        return text
    
    def _detect_code_language(self, code: str) -> str:
        """Detect programming language from code content."""
        code_lower = code.lower()
        
        # Score each language based on keyword matches
        language_scores = {}
        
        for language, keywords in self.LANGUAGE_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in code_lower:
                    score += 1
            
            if score > 0:
                language_scores[language] = score
        
        # Return language with highest score
        if language_scores:
            return max(language_scores, key=language_scores.get)
        
        return ""
    
    def _smart_truncate(self, text: str, max_length: int) -> Tuple[str, bool, bool]:
        """Smart truncation that preserves meaning."""
        if len(text) <= max_length:
            return text, False, False
        
        if self.config.truncation_strategy == "word":
            return self._truncate_by_word(text, max_length)
        elif self.config.truncation_strategy == "character":
            return self._truncate_by_character(text, max_length)
        else:  # smart
            return self._truncate_smart(text, max_length)
    
    def _truncate_smart(self, text: str, max_length: int) -> Tuple[str, bool, bool]:
        """Smart truncation that tries to preserve sentence boundaries."""
        if len(text) <= max_length:
            return text, False, False
        
        # Try to find a good breaking point
        truncate_point = max_length - 20  # Leave room for ellipsis and "Show more"
        
        # Look for sentence boundaries
        sentence_endings = ['. ', '! ', '? ', '\n\n']
        best_break = 0
        
        for ending in sentence_endings:
            pos = text.rfind(ending, 0, truncate_point)
            if pos > best_break:
                best_break = pos + len(ending)
        
        # If no good sentence break, try paragraph breaks
        if best_break < truncate_point * 0.7:
            pos = text.rfind('\n', 0, truncate_point)
            if pos > best_break:
                best_break = pos
        
        # If still no good break, use word boundary
        if best_break < truncate_point * 0.5:
            pos = text.rfind(' ', 0, truncate_point)
            if pos > 0:
                best_break = pos
            else:
                best_break = truncate_point
        
        truncated_text = text[:best_break].rstrip()
        
        # Add ellipsis and show more indicator
        if len(text) > max_length:
            remaining_chars = len(text) - best_break
            truncated_text += f"... _{remaining_chars} more characters_"
        
        return truncated_text, True, True
    
    def _truncate_by_word(self, text: str, max_length: int) -> Tuple[str, bool, bool]:
        """Truncate by word boundaries."""
        if len(text) <= max_length:
            return text, False, False
        
        words = text.split()
        truncated_words = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_length - 20:  # Leave room for ellipsis
                break
            truncated_words.append(word)
            current_length += len(word) + 1
        
        truncated_text = ' '.join(truncated_words)
        remaining_words = len(words) - len(truncated_words)
        
        if remaining_words > 0:
            truncated_text += f"... _{remaining_words} more words_"
        
        return truncated_text, True, True
    
    def _truncate_by_character(self, text: str, max_length: int) -> Tuple[str, bool, bool]:
        """Simple character-based truncation."""
        if len(text) <= max_length:
            return text, False, False
        
        truncate_point = max_length - 20
        truncated_text = text[:truncate_point]
        remaining_chars = len(text) - truncate_point
        
        truncated_text += f"... _{remaining_chars} more characters_"
        
        return truncated_text, True, True
    
    def create_show_more_button(self, full_text: str, preview_text: str) -> Dict[str, Any]:
        """Create a 'Show More' button for truncated content."""
        # Create a hash of the full text for identification
        content_hash = hashlib.md5(full_text.encode()).hexdigest()[:8]
        
        return {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Show More",
                "emoji": True
            },
            "action_id": f"show_more_{content_hash}",
            "value": content_hash
        }
    
    def format_code_diff(self, diff_content: str, file_path: str = "") -> str:
        """Format code diff for display."""
        lines = diff_content.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.startswith('+'):
                formatted_lines.append(f"+ {line[1:]}")
            elif line.startswith('-'):
                formatted_lines.append(f"- {line[1:]}")
            elif line.startswith('@@'):
                formatted_lines.append(f"📍 {line}")
            else:
                formatted_lines.append(f"  {line}")
        
        formatted_diff = '\n'.join(formatted_lines)
        
        if file_path:
            return f"*File: `{file_path}`*\n```diff\n{formatted_diff}\n```"
        else:
            return f"```diff\n{formatted_diff}\n```"
    
    def create_preview_mode(self, text: str, preview_length: int = 150) -> Dict[str, str]:
        """Create preview and full versions of text."""
        if len(text) <= preview_length:
            return {
                'preview': text,
                'full': text,
                'needs_expansion': False
            }
        
        # Smart preview that tries to end at sentence boundary
        preview_point = preview_length
        sentence_end = text.rfind('. ', 0, preview_point)
        
        if sentence_end > preview_length * 0.7:
            preview_point = sentence_end + 1
        
        preview = text[:preview_point].rstrip()
        if len(text) > preview_point:
            preview += "..."
        
        return {
            'preview': preview,
            'full': text,
            'needs_expansion': True
        }
    
    def sanitize_text(self, text: str) -> str:
        """Sanitize text for security."""
        # HTML escape
        text = html.escape(text)
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'on\w+\s*=',  # onclick, onload, etc.
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def get_processing_stats(self, text: str) -> Dict[str, Any]:
        """Get statistics about text processing."""
        return {
            'character_count': len(text),
            'word_count': len(text.split()),
            'line_count': len(text.split('\n')),
            'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
            'has_code_blocks': bool(self.PATTERNS['code_block'].search(text)),
            'has_links': bool(self.PATTERNS['url'].search(text)),
            'has_mentions': bool(self.PATTERNS['user_mention'].search(text)),
            'estimated_read_time_seconds': len(text.split()) * 0.25  # ~240 WPM
        }


# Global default instance
default_text_processor = TextProcessor()