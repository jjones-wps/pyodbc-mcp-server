# Branch Protection Setup

This document describes the recommended branch protection settings for the repository.

## GitHub Branch Protection Rules

### Configure via GitHub UI

1. Go to **Settings** → **Branches**
2. Click **Add branch protection rule**
3. Configure as follows:

### Branch name pattern

```
master
```

(Also add a rule for `main` if you plan to rename)

### Protection Settings

#### Required Settings (Recommended)

| Setting | Value | Reason |
|---------|-------|--------|
| **Require a pull request before merging** | ✅ Enabled | All changes go through PR review |
| **Require approvals** | 0 (or 1 for team projects) | Solo projects can set to 0 |
| **Dismiss stale pull request approvals** | ✅ Enabled | Re-review after changes |
| **Require status checks to pass** | ✅ Enabled | CI must pass before merge |
| **Require branches to be up to date** | ✅ Enabled | Must be current with base |
| **Status checks that are required** | `lint`, `test`, `build` | From CI workflow |

#### Additional Settings

| Setting | Value | Reason |
|---------|-------|--------|
| **Require conversation resolution** | ✅ Enabled | All comments must be resolved |
| **Do not allow bypassing settings** | ✅ Enabled | Even admins follow the rules |
| **Allow force pushes** | ❌ Disabled | Protect history |
| **Allow deletions** | ❌ Disabled | Protect branch |

### Quick Setup via gh CLI

```bash
# Enable branch protection with required status checks
gh api repos/jjones-wps/pyodbc-mcp-server/branches/master/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["lint","test (3.10)","test (3.11)","test (3.12)","build"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":0,"dismiss_stale_reviews":true}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

### Verify Protection

```bash
gh api repos/jjones-wps/pyodbc-mcp-server/branches/master/protection
```

## Workflow

With branch protection enabled:

1. **Create feature branch** from `master`
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. **Push and create PR**
   ```bash
   git push -u origin feature/my-feature
   gh pr create --fill
   ```

4. **Wait for CI checks** to pass

5. **Merge PR** (via GitHub UI or CLI)
   ```bash
   gh pr merge --squash
   ```

## CI Status Checks

The following checks must pass before merging:

| Check | Workflow | Description |
|-------|----------|-------------|
| `lint` | ci.yml | Ruff linting and formatting |
| `test (3.10)` | ci.yml | Tests on Python 3.10 |
| `test (3.11)` | ci.yml | Tests on Python 3.11 |
| `test (3.12)` | ci.yml | Tests on Python 3.12 |
| `build` | ci.yml | Package builds successfully |

## Exceptions

For emergency fixes that need to bypass protection:

1. **Repository admins** can temporarily disable protection
2. Make the fix
3. **Re-enable protection immediately**
4. Document the bypass in the PR/commit

This should be rare and only for critical production issues.
