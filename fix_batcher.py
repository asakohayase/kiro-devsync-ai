#!/usr/bin/env python3
"""Script to fix the BatchFormatterContext class in message_batcher.py"""

def fix_batcher():
    with open('devsync_ai/core/message_batcher.py', 'r') as f:
        lines = f.readlines()
    
    # Find and remove incomplete BatchFormatterContext definitions
    new_lines = []
    skip_until_next_class = False
    
    for i, line in enumerate(lines):
        if 'class BatchFormatterContext:' in line and 'batch_group: \'BatchGroup\'' in ''.join(lines[i:i+5]):
            # This is an incomplete definition, skip it
            skip_until_next_class = True
            continue
        
        if skip_until_next_class:
            if line.strip().startswith('class ') or line.strip().startswith('@dataclass'):
                skip_until_next_class = False
                new_lines.append(line)
            continue
        
        new_lines.append(line)
    
    # Find where to insert the complete BatchFormatterContext class
    # Insert it after BatchGroup class
    insert_index = -1
    for i, line in enumerate(new_lines):
        if 'return age_minutes >= max_age_minutes' in line:
            insert_index = i + 1
            break
    
    if insert_index != -1:
        # Insert the complete BatchFormatterContext class
        batch_formatter_context = '''

@dataclass
class BatchFormatterContext:
    """Context for batch message formatting with SlackMessageFormatterFactory."""
    batch_group: 'BatchGroup'
    channel_id: str
    message_count: int
    content_types: Dict[str, int]
    authors: List[str]
    time_range: Dict[str, datetime]
    formatter_factory: Optional['SlackMessageFormatterFactory'] = None
    
    def get_message_type(self) -> MessageType:
        """Determine the appropriate message type for the batch."""
        # Determine batch message type based on content
        if len(self.content_types) == 1:
            content_type = list(self.content_types.keys())[0]
            if content_type == 'pr_update':
                return MessageType.PR_BATCH
            elif content_type == 'jira_update':
                return MessageType.JIRA_BATCH
        
        # Default to custom batch type for mixed content
        return MessageType.CUSTOM
    
    def get_formatter_data(self) -> Dict[str, Any]:
        """Get data formatted for SlackMessageFormatterFactory."""
        stats = self.batch_group.get_summary_stats()
        
        return {
            'batch_id': self.batch_group.id,
            'batch_type': self.batch_group.batch_type.value,
            'channel_id': self.channel_id,
            'message_count': self.message_count,
            'content_types': dict(self.content_types),
            'authors': self.authors,
            'time_range': {
                'start': self.time_range.get('start').isoformat() if self.time_range.get('start') else None,
                'end': self.time_range.get('end').isoformat() if self.time_range.get('end') else None
            },
            'messages': [
                {
                    'id': msg.id,
                    'content_type': msg.content_type.value,
                    'timestamp': msg.timestamp.isoformat(),
                    'author': msg.author,
                    'priority': msg.priority,
                    'data': msg.data,
                    'metadata': msg.metadata
                }
                for msg in self.batch_group.messages
            ],
            'created_at': self.batch_group.created_at.isoformat(),
            'expires_at': self.batch_group.expires_at.isoformat() if self.batch_group.expires_at else None,
            'metadata': self.batch_group.metadata
        }

'''
        new_lines.insert(insert_index, batch_formatter_context)
    
    # Write the fixed file
    with open('devsync_ai/core/message_batcher.py', 'w') as f:
        f.writelines(new_lines)
    
    print("Fixed BatchFormatterContext class")

if __name__ == "__main__":
    fix_batcher()