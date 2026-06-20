# Security Policy

## Reporting

If you discover a security issue, do not open a public issue with exploit details.
Report it privately to the maintainers and include:

- A clear description of the issue
- Steps to reproduce it
- The affected version or commit, if known
- Any suggested remediation

## Secrets

This repository includes a secret scan for Gemini API keys in tracked files and staged additions.
Run `uv run poe secret-scan` for a full repository scan and `uv run poe secret-scan-staged` before committing if needed.
