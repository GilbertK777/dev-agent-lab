# dev-agent-lab

A learning project for building a decision-support Agent.

## Purpose

This project explores how to build an Agent that helps developers reason through
software architecture decisions. The focus is on structured reasoning and
trade-off analysis, not on automating decisions.

## What the Agent Does

- Helps evaluate architectural trade-offs (e.g., monolith vs microservices)
- Presents options with pros, cons, assumptions, and constraints
- Provides recommendations with clear reasoning
- Asks clarifying questions when context is missing

## What the Agent Does Not Do

- Make final decisions on behalf of the developer
- Automatically execute code or modify files
- Assume missing context or requirements

## Project Structure

```
dev-agent-lab/
├── src/
│   ├── observation/   # Context gathering
│   ├── reasoning/     # Trade-off analysis
│   └── proposal/      # Recommendation generation
├── tests/
├── CLAUDE.md          # AI assistant guidelines
└── README.md
```

## Tech Stack

- Python
- Standard libraries preferred
- Focus on clarity over frameworks

## Guiding Principle

> When in doubt, prefer clarity and explanation over speed or completeness.

## License

TBD
