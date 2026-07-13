# Contributing to TrainForge

Thank you for considering an improvement to TrainForge. Focused bug fixes, tests, accessibility improvements, and documentation corrections are welcome.

## Before You Start

- Search existing issues before opening a new one.
- Use the bug or feature template and include enough context to reproduce or evaluate the request.
- Keep each pull request focused on one change.
- Never include real client information, credentials, database files, or API keys.

Security vulnerabilities should be reported privately according to [SECURITY.md](SECURITY.md), not through a public issue.

## Development Setup

Follow the [installation guide](README.md#installation-guide), then run:

```bash
python manage.py migrate
python manage.py runserver
```

The project uses server-rendered Django templates and HTMX; there is no separate frontend build step.

## Verification

Before submitting a pull request, run:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

If your change affects static-file handling, also run:

```bash
python manage.py collectstatic --noinput
```

## Pull Requests

In the pull request description:

- Explain the problem and the chosen solution.
- List the checks you ran.
- Include screenshots for visible UI changes, using fictional data only.
- Call out migrations, configuration changes, and compatibility considerations.

By contributing, you agree that your contribution will be licensed under the project's [MIT License](LICENSE).
