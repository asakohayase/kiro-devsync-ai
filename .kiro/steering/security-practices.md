# Security Practices

## Critical Security Rules

### Never Hardcode Sensitive Information
- **NEVER** hardcode API keys, tokens, passwords, or other sensitive data in configuration files
- **NEVER** commit sensitive information to version control
- **NEVER** expose sensitive data in code examples, logs, or documentation

### Environment Variables
- Always use environment variables for sensitive configuration
- Use placeholder syntax like `${VARIABLE_NAME}` in configuration files
- Store actual values in `.env` files that are gitignored

### Examples of What NOT to Do
```json
// ❌ WRONG - Never do this
{
  "env": {
    "API_KEY": "sk-1234567890abcdef"
  }
}
```

### Examples of What TO Do
```json
// ✅ CORRECT - Use environment variable placeholders
{
  "env": {
    "API_KEY": "${API_KEY}"
  }
}
```

### MCP Configuration Security
- MCP server configurations must use environment variable placeholders
- Never hardcode project IDs, access tokens, or API keys in `mcp.json`
- Ensure all sensitive values are loaded from environment variables

### Code Review Checklist
Before any configuration changes:
- [ ] No hardcoded API keys or tokens
- [ ] All sensitive values use environment variable syntax
- [ ] `.env` file contains actual values (and is gitignored)
- [ ] No sensitive data in commit messages or code comments

## Immediate Actions Required
If sensitive data is accidentally committed:
1. Immediately revoke/rotate the exposed credentials
2. Remove the sensitive data from the repository
3. Update configuration to use environment variables
4. Verify `.env` file is properly gitignored