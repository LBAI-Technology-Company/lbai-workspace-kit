# REVIEW_REQUIRED_BOUNDARY

## Review Reminder Required

Remind the employee that responsible leader review is required before external release when tasks involve:

- Public-facing content
- Website release copy
- Company positioning for external use
- Pricing
- Legal or compliance claims
- Investor material
- Media statements
- Product capability claims
- Customer-facing promises
- Hiring-sensitive judgment
- Finance-sensitive content
- Security-sensitive content

This workflow does not block execution or finish solely because review-sensitive content is present.

## Status Rule

Review-sensitive work must not be marked:

- `APPROVED`
- `FINAL`
- `PUBLIC_READY`
- `RELEASED`

Tasks may finish as `COMPLETED` while `review_needed: true` and `leader_review_reminder` are set. External release still requires responsible reviewer approval outside this workflow.
