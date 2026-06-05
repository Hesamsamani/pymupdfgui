# Security Policy

## Supported versions

Only the latest released version of Distilmark receives security fixes. Older versions are not patched — please update before reporting.

| Version | Supported          |
| ------- | ------------------ |
| 1.2.x   | :white_check_mark: |
| < 1.2   | :x:                |

## Reporting a vulnerability

If you've found a security issue in Distilmark, please **do not open a public issue**. Instead, report it privately one of these ways:

1. **GitHub Security Advisory** (preferred) — use the **Report a vulnerability** button on the [Security tab](https://github.com/Hesamsamani/pymupdfgui/security/advisories/new). This keeps the discussion private until a fix ships.
2. **Email** — `hesamghsamani@gmail.com` with subject line starting `[Distilmark security]`.

Please include:

- A description of the issue and what an attacker could do with it.
- Steps to reproduce (a sample PDF or minimal repro is ideal).
- The Distilmark version and OS you tested on.

## What to expect

- Acknowledgement within **7 days**.
- A fix or mitigation plan within **30 days** for confirmed vulnerabilities. Complex issues may take longer; we'll keep you updated.
- Credit in the release notes if you'd like it (let us know your preferred name / handle).

## Scope

In scope:

- The Distilmark desktop app and its bundled `.exe` releases.
- The Python package (`distilmark` on PyPI / GitHub).
- The conversion engines we ship (PyMuPDF, pdfplumber, LLM clients).

Out of scope:

- Vulnerabilities in upstream dependencies (please report those upstream — PyMuPDF, PyQt6, Ollama, etc.).
- Issues that require an attacker to already control the user's machine.
- Social-engineering attacks (e.g. tricking a user into running a malicious PDF that exploits a flaw they introduced themselves by modifying source).

Thanks for helping keep Distilmark users safe.
