# Patchy 🛡️

> Multi-Agent AI Security Bot for GitHub Repositories

Patchy automates vulnerability detection, generates precise code fixes, and manages security issues in your GitHub repos using a multi-agent AI architecture powered by Cerebras LLM.

## Features

- **🔍 Auto-scan vulnerabilities** — Run Semgrep security scans on your repositories
- **🔧 Generate fixes automatically** — AI-powered code patches for detected issues  
- **📋 Create PRs** — Automatic pull requests with fixes ready to merge
- **💬 Issue interaction** — @mention Patchy in GitHub issues for AI-powered analysis

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask (Python) |
| Frontend | HTML + TailwindCSS + Vanilla JS |
| Auth | GitHub OAuth |
| Scanner | Semgrep |
| LLM | Cerebras (qwen-3-235b) |
| Storage | JSON file |

## Project Structure

```
patchy/
├── TECHNICAL_SPEC.md          # Technical specifications
├── TODO.md                    # Task breakdown
├── DESIGN.md                  # UI/UX design specs
├── STITCH_PROMPTS.md          # Design prompts for Stitch
├── OPUS_PROMPT.md             # Frontend build instructions
├── OPUS_REVIEW_PROMPT.md      # Planning review prompt
└── README.md                  # This file
```

## Quick Start

Coming soon! The project is currently in the planning phase.

## Development Timeline

- **Day 1**: Core functionality (OAuth, scanning, fix generation, PR creation)
- **Day 2**: Issue interaction, UI polish, testing

## Documentation

- [Technical Specification](TECHNICAL_SPEC.md) - Architecture and implementation details
- [TODO List](TODO.md) - Task breakdown and progress tracking
- [Design Specification](DESIGN.md) - UI/UX guidelines
- [Stitch Prompts](STITCH_PROMPTS.md) - Design generation prompts
- [Frontend Build Guide](OPUS_PROMPT.md) - Instructions for building the frontend
- [Planning Review](OPUS_REVIEW_PROMPT.md) - Comprehensive planning review prompt

## Evolution from SentryAgent

Patchy extends the multi-agent security architecture from SentryAgent (smart contract security) to general application security, adding:
- Web interface with GitHub integration
- Broader language support
- Automated PR creation
- Conversational issue interaction

## License

MIT

---

**Status**: 🚧 Planning Phase  
**Timeline**: 1-2 days  
**Last Updated**: 2026-04-23
