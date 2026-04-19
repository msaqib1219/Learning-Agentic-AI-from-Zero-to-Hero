# 📦 Archives - Historical Files & Deprecated Components

This folder contains old files, migration guides, and deprecated components that are no longer part of the active project.

## 📁 Folder Structure

### `/deprecated/`
- **auth-server/** — Old separate authentication server (replaced by better-auth integration in main backend)
- **build/** — Old build artifacts and configuration

### `/tests/`
- **test_*.py** — Old unit/integration tests (replaced by future comprehensive test suite)
- **comprehensive_test.py** — Old comprehensive test script
- **direct_test.py** — Old direct API test script
- **run_test*.py** — Old test runner scripts

### `/migration/`
- **MIGRATION_QUICK_START.md** — Migration guide from Railway to SnapDeploy (superseded by DEPLOYMENT_PLAN.md)
- **railway.toml** — Railway deployment config (legacy)
- **render.yaml** — Render.com deployment config (tested but not used)
- **Dockerfile** — Docker build config (archived for reference)
- **nixpacks.toml** — Nixpacks build config
- **Procfile** — Heroku-style process file

### `/docs/`
Reserved for historical documentation and guides.

---

## 🔄 When to Use These Files

**DO NOT** use files from this archive for the current project unless:
1. You're documenting historical decisions (ADRs, PHRs)
2. You need a reference for how something used to work
3. Explicitly stated in the project plan

**TO REFERENCE** migration history:
- See `/history/prompts/` for Prompt History Records (PHRs)
- See `/history/adr/` for Architectural Decision Records (ADRs)

---

## 📝 How Files Got Here

- **2026-04-19**: Archived old files during Phase A setup cleanup
  - Reason: Consolidate project structure for learning MVP
  - Decision: Keep for reference, don't include in active development

---

## ♻️ Future Cleanup

If you later decide to delete these files permanently:
```bash
rm -rf archives/
# But commit git log first for reference!
git log --oneline -- archives/
```

---

**Last Updated:** 2026-04-19  
**Related Plan:** See `.claude/DEPLOYMENT_PLAN.md`
