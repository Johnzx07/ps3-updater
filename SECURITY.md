# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | Yes       |

Only the latest release is supported. Older releases, if any, are not patched.

## Reporting a vulnerability

This is a small personal project maintained by one person. **There is no
dedicated security email or private reporting channel**, and we do not want to
publish contact details that are not actually monitored.

To report a security issue:

- Open an **issue** on this repository describing the problem. If you prefer it
  to stay out of sight, keep the description high-level (what is affected and how
  to reproduce) rather than including full exploit detail in public text.
- For a private repository, only people with access can see issues — use that if
  you have been granted access.

## What to include

When reporting, please provide:

- The version of the app (see `CHANGELOG.md`).
- Steps to reproduce the issue.
- Any relevant error messages or console output.
- Your operating system and Python version.

## Acknowledgment & disclosure expectations

Because this is a single-maintainer personal project with no formal security
process, we cannot guarantee a specific response time or a coordinated-disclosure
timeline. We will do our best to acknowledge reports and address genuine issues in
a future release. Please avoid publicly disclosing an unpatched vulnerability here;
use the issue channel above instead.

## Scope note

The app only talks to Sony's public PSN update endpoints (the same ones a real
console uses) and only fetches updates for title IDs present in your own RPCS3
`games.yml`. It does not store credentials, does not require an account, and makes
no network calls beyond those endpoints. See the README "Security" section for the
TLS/`verify=False` behavior of those two Sony requests.
