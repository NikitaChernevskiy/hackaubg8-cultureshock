# Contributing — CultureShock

## Branch Strategy
- `main` — stable, deployable code
- `dev` — integration branch (merge features here first)
- `feature/<name>` — individual features
- `fix/<name>` — bug fixes

## Workflow
1. Pull latest `dev`: `git pull origin dev`
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit often with clear messages
4. Push and open PR to `dev`
5. After review, merge to `dev`
6. `dev` → `main` when stable

## Commit Messages
Use conventional commits:
- `feat: add login page`
- `fix: resolve API timeout`
- `docs: update README`
- `infra: add Azure deployment`
- `style: fix formatting`

## Quick Commands
```bash
git checkout dev && git pull
git checkout -b feature/my-feature
# ... code ...
git add . && git commit -m "feat: description"
git push origin feature/my-feature
```
