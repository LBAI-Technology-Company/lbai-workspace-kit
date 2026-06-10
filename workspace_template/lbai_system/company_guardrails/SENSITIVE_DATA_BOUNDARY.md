# SENSITIVE_DATA_BOUNDARY

## Never Write To Repo Artifacts

Do not write the following into repo artifacts:

- Passwords
- API keys
- Access tokens
- Secret tokens
- Private keys
- Customer confidential data
- Regulated data
- Financial account information
- Legal privileged communication
- Candidate sensitive personal information beyond necessity
- Unnecessary personal data such as email addresses or phone numbers
- Private source code without approval

## Redaction

If sensitive information appears in user input, replace it with:

```text
[SENSITIVE INFORMATION REDACTED - USE APPROVED SECURE CHANNEL]
```

Private GitHub repositories are still company artifact ledgers. They are not secure secret stores.
