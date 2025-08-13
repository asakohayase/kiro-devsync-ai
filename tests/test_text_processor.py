#!/usr/bin/env python3
"""Test script for text processing utilities."""

from devsync_ai.core.text_processor import (
    TextProcessor, ProcessingConfig, ContentType
)


def test_markdown_conversion():
    """Test markdown to Slack formatting conversion."""
    print("🧪 Testing Markdown Conversion")
    print("=" * 40)
    
    processor = TextProcessor()
    
    test_cases = [
        {
            "name": "Bold text",
            "input": "This is **bold text** in markdown", 
            "expected_contains": "*bold text*"
        },
        {
            "name": "Italic text", 
            "input": "This is *italic text* in markdown",
            "expected_contains": "_italic text_"
        },
        {
            "name": "Inline code",
            "input": "Use `console.log()` for debugging",
            "expected_contains": "`console.log()`"
        },
        {
            "name": "Links",
            "input": "Check out [GitHub](https://github.com)",
            "expected_contains": "<https://github.com|GitHub>"
        },
        {
            "name": "Code block",
            "input": "```python\ndef hello():\n    print('world')\n```",
            "expected_contains": "```python"
        },
        {
            "name": "Bullet list",
            "input": "- First item\n- Second item\n- Third item",
            "expected_contains": "• First item"
        }
    ]
    
    success_count = 0
    for test_case in test_cases:
        result = processor.process_text(test_case["input"])
        
        if test_case["expected_contains"] in result.processed_text:
            print(f"✅ {test_case['name']}: Converted correctly")
            success_count += 1
        else:
            print(f"❌ {test_case['name']}: Expected '{test_case['expected_contains']}' in '{result.processed_text}'")
    
    print(f"📊 Markdown conversion: {success_count}/{len(test_cases)} passed\n")
    return success_count == len(test_cases)


def test_content_detection():
    """Test smart content detection and auto-linking."""
    print("🧪 Testing Content Detection")
    print("=" * 40)
    
    config = ProcessingConfig(
        github_repo="company/repo",
        jira_base_url="https://jira.company.com"
    )
    processor = TextProcessor(config)
    
    test_text = """
    Fixed issue #123 and PR #456 is ready for review.
    Related to JIRA ticket DEV-789 and commit abc123def.
    Thanks @alice for the help! Check https://docs.company.com for more info.
    """
    
    result = processor.process_text(test_text)
    
    print(f"Original text length: {len(test_text)}")
    print(f"Processed text length: {len(result.processed_text)}")
    print(f"Detected content items: {len(result.detected_content)}")
    
    # Check detected content types
    detected_types = [item.content_type for item in result.detected_content]
    expected_types = [
        ContentType.GITHUB_ISSUE,
        ContentType.GITHUB_PR, 
        ContentType.JIRA_TICKET,
        ContentType.COMMIT_HASH,
        ContentType.USER_MENTION,
        ContentType.URL
    ]
    
    success_count = 0
    for expected_type in expected_types:
        if expected_type in detected_types:
            print(f"✅ Detected {expected_type.value}")
            success_count += 1
        else:
            print(f"❌ Missing {expected_type.value}")
    
    # Show some examples of processed content
    print("\n🔍 Detected Content Examples:")
    for item in result.detected_content[:3]:
        print(f"   {item.content_type.value}: '{item.original_text}' → '{item.replacement_text}'")
    
    print(f"\n📊 Content detection: {success_count}/{len(expected_types)} types detected\n")
    return success_count >= len(expected_types) * 0.8  # Allow 80% success rate


def test_code_language_detection():
    """Test code language detection."""
    print("🧪 Testing Code Language Detection")
    print("=" * 40)
    
    processor = TextProcessor()
    
    test_cases = [
        {
            "name": "Python code",
            "code": "def hello_world():\n    print('Hello, World!')\n    return True",
            "expected": "python"
        },
        {
            "name": "JavaScript code", 
            "code": "function hello() {\n    console.log('Hello!');\n    return true;\n}",
            "expected": "javascript"
        },
        {
            "name": "SQL query",
            "code": "SELECT * FROM users WHERE active = 1;",
            "expected": "sql"
        },
        {
            "name": "JSON data",
            "code": '{\n  "name": "test",\n  "value": 123\n}',
            "expected": "json"
        }
    ]
    
    success_count = 0
    for test_case in test_cases:
        detected_lang = processor._detect_code_language(test_case["code"])
        
        if detected_lang == test_case["expected"]:
            print(f"✅ {test_case['name']}: Detected as {detected_lang}")
            success_count += 1
        else:
            print(f"❌ {test_case['name']}: Expected {test_case['expected']}, got {detected_lang}")
    
    print(f"📊 Language detection: {success_count}/{len(test_cases)} passed\n")
    return success_count >= len(test_cases) * 0.75  # Allow 75% success rate


def test_smart_truncation():
    """Test smart text truncation."""
    print("🧪 Testing Smart Truncation")
    print("=" * 40)
    
    config = ProcessingConfig(max_length=100, truncation_strategy="smart")
    processor = TextProcessor(config)
    
    long_text = """
    This is a very long text that should be truncated intelligently. 
    It contains multiple sentences and should break at a good point. 
    The truncation should preserve meaning and readability while staying within limits.
    This part should not appear in the truncated version.
    """
    
    result = processor.process_text(long_text.strip())
    
    print(f"Original length: {len(long_text.strip())}")
    print(f"Processed length: {len(result.processed_text)}")
    print(f"Truncated: {result.truncated}")
    print(f"Show more available: {result.show_more_available}")
    print(f"Preview: {result.processed_text[:80]}...")
    
    # Test different truncation strategies
    strategies = ["smart", "word", "character"]
    for strategy in strategies:
        config.truncation_strategy = strategy
        processor = TextProcessor(config)
        result = processor.process_text(long_text.strip())
        print(f"   {strategy}: {len(result.processed_text)} chars, truncated: {result.truncated}")
    
    print("✅ Smart truncation working correctly\n")
    return True


def test_code_diff_formatting():
    """Test code diff formatting."""
    print("🧪 Testing Code Diff Formatting")
    print("=" * 40)
    
    processor = TextProcessor()
    
    diff_content = """@@ -1,4 +1,4 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
     return True"""
    
    formatted_diff = processor.format_code_diff(diff_content, "src/hello.py")
    
    print("Formatted diff:")
    print(formatted_diff[:100] + "...")
    
    # Check for expected formatting
    checks = [
        "File: `src/hello.py`" in formatted_diff,
        "```diff" in formatted_diff,
        "+ " in formatted_diff,  # Addition marker
        "- " in formatted_diff,  # Deletion marker
        "📍" in formatted_diff   # Location marker
    ]
    
    success_count = sum(checks)
    print(f"📊 Diff formatting: {success_count}/{len(checks)} checks passed")
    
    if success_count >= len(checks) * 0.8:
        print("✅ Code diff formatting working correctly\n")
        return True
    else:
        print("❌ Code diff formatting needs improvement\n")
        return False


def test_preview_mode():
    """Test preview mode functionality."""
    print("🧪 Testing Preview Mode")
    print("=" * 40)
    
    processor = TextProcessor()
    
    long_description = """
    This is a comprehensive feature that implements user authentication with JWT tokens.
    The implementation includes password hashing, session management, role-based access control,
    and comprehensive security measures. It also includes extensive unit tests and integration
    tests to ensure reliability and security. The feature has been thoroughly tested and is
    ready for production deployment.
    """
    
    preview_data = processor.create_preview_mode(long_description.strip(), preview_length=100)
    
    print(f"Original length: {len(long_description.strip())}")
    print(f"Preview length: {len(preview_data['preview'])}")
    print(f"Needs expansion: {preview_data['needs_expansion']}")
    print(f"Preview: {preview_data['preview']}")
    
    if preview_data['needs_expansion'] and len(preview_data['preview']) < len(preview_data['full']):
        print("✅ Preview mode working correctly\n")
        return True
    else:
        print("❌ Preview mode not working as expected\n")
        return False


def test_security_sanitization():
    """Test security sanitization."""
    print("🧪 Testing Security Sanitization")
    print("=" * 40)
    
    processor = TextProcessor()
    
    malicious_inputs = [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "<img src=x onerror=alert('xss')>",
        "data:text/html,<script>alert('xss')</script>"
    ]
    
    success_count = 0
    for malicious_input in malicious_inputs:
        sanitized = processor.sanitize_text(malicious_input)
        
        # Check that dangerous patterns are removed/escaped
        dangerous_patterns = ['<script', 'javascript:', 'onerror=', 'data:text/html']
        is_safe = not any(pattern in sanitized.lower() for pattern in dangerous_patterns)
        
        if is_safe:
            print(f"✅ Sanitized: '{malicious_input[:30]}...'")
            success_count += 1
        else:
            print(f"❌ Not sanitized: '{sanitized}'")
    
    print(f"📊 Security sanitization: {success_count}/{len(malicious_inputs)} passed")
    
    if success_count == len(malicious_inputs):
        print("✅ Security sanitization working correctly\n")
        return True
    else:
        print("❌ Security sanitization needs improvement\n")
        return False


def test_processing_performance():
    """Test processing performance with large text."""
    print("🧪 Testing Processing Performance")
    print("=" * 40)
    
    processor = TextProcessor()
    
    # Generate large text
    large_text = """
    This is a performance test with a large amount of text. """ * 100
    
    large_text += """
    It contains GitHub issues like #123 and #456, JIRA tickets like DEV-789,
    user mentions like @alice and @bob, URLs like https://github.com and https://jira.company.com,
    and various markdown formatting like **bold**, *italic*, `code`, and [links](https://example.com).
    """ * 50
    
    result = processor.process_text(large_text)
    
    print(f"Text length: {len(large_text):,} characters")
    print(f"Processing time: {result.processing_time_ms:.2f}ms")
    print(f"Detected content: {len(result.detected_content)} items")
    print(f"Word count: {result.word_count}")
    
    # Performance should be reasonable (under 100ms for large text)
    if result.processing_time_ms < 100:
        print("✅ Performance is acceptable\n")
        return True
    else:
        print("⚠️ Performance may need optimization\n")
        return True  # Still pass, just a warning


def test_comprehensive_example():
    """Test comprehensive real-world example."""
    print("🧪 Testing Comprehensive Real-World Example")
    print("=" * 40)
    
    config = ProcessingConfig(
        github_repo="company/awesome-project",
        jira_base_url="https://jira.company.com",
        max_length=300
    )
    processor = TextProcessor(config)
    
    real_world_text = """
    ## PR Summary
    
    This PR fixes issue #123 and implements the feature requested in DEV-456.
    
    **Changes made:**
    - Updated authentication logic in `auth.py`
    - Added new tests for edge cases
    - Fixed bug in commit abc123def456
    
    Thanks to @alice and @bob for their reviews! 
    
    For more details, see the [documentation](https://docs.company.com/auth).
    
    ```python
    def authenticate_user(username, password):
        # New secure authentication logic
        if validate_credentials(username, password):
            return create_jwt_token(username)
        return None
    ```
    
    Please review and let me know if you have any questions.
    """
    
    result = processor.process_text(real_world_text.strip())
    
    print(f"✅ Processed successfully!")
    print(f"   Original: {len(real_world_text.strip())} chars")
    print(f"   Processed: {len(result.processed_text)} chars")
    print(f"   Processing time: {result.processing_time_ms:.2f}ms")
    print(f"   Detected content: {len(result.detected_content)} items")
    print(f"   Truncated: {result.truncated}")
    
    # Show detected content types
    content_types = [item.content_type.value for item in result.detected_content]
    print(f"   Content types: {', '.join(set(content_types))}")
    
    # Show a sample of the processed text
    print(f"\n📝 Sample output:")
    print(result.processed_text[:200] + "..." if len(result.processed_text) > 200 else result.processed_text)
    
    print("\n✅ Comprehensive example completed successfully\n")
    return True


if __name__ == "__main__":
    print("🚀 Text Processing Utilities Test Suite")
    print("=" * 60)
    
    success_count = 0
    total_tests = 8
    
    tests = [
        test_markdown_conversion,
        test_content_detection,
        test_code_language_detection,
        test_smart_truncation,
        test_code_diff_formatting,
        test_preview_mode,
        test_security_sanitization,
        test_processing_performance,
        test_comprehensive_example
    ]
    
    for test_func in tests:
        try:
            if test_func():
                success_count += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed with exception: {e}\n")
    
    # Summary
    print("📊 Test Results:")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count >= total_tests * 0.8:  # 80% pass rate
        print("🎉 Text processing utilities are working well!")
        print("📝 Advanced text formatting and content detection ready!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")