# v0.4.0 Release Status

**Date**: 2026-01-03
**Status**: GitHub Release ✅ Complete | PyPI Publishing ⏳ Pending Configuration

---

## ✅ Completed

### 1. Version Bump
- Updated `pyproject.toml` version to 0.4.0
- Committed: `75a5fba`

### 2. CHANGELOG Updated
- Added comprehensive v0.4.0 entry with all Phase 3 work
- Committed: `1233845`

### 3. GitHub Release Created
- **Tag**: v0.4.0
- **URL**: https://github.com/jjones-wps/pyodbc-mcp-server/releases/tag/v0.4.0
- **Release Notes**: Comprehensive (covers all Phase 3 achievements)
- **Build Artifacts**: ✅ Attached to release
  - `pyodbc_mcp_server-0.4.0-py3-none-any.whl` (23KB)
  - `pyodbc_mcp_server-0.4.0.tar.gz` (126KB)

### 4. Release Workflow Updated
- Enabled PyPI publishing in `.github/workflows/release.yml`
- Added `publish-test-pypi` job (Test PyPI)
- Added `publish-pypi` job (Production PyPI)
- Uses GitHub trusted publishing (secure, no API tokens needed)
- Committed: `9a629a7`

### 5. Local Build
- Package built successfully: `dist/pyodbc_mcp_server-0.4.0.*`
- Ready for manual upload if needed

---

## ⏳ Pending: PyPI Publishing

The GitHub Actions workflow is now configured to publish to both Test PyPI and Production PyPI, but **GitHub trusted publishing must be configured first**.

### Why Trusted Publishing?

GitHub's trusted publishing is **more secure** than API tokens:
- ✅ No secrets to manage or rotate
- ✅ No tokens that can be leaked
- ✅ Automatic authentication via OIDC
- ✅ Per-repository, per-workflow permissions

---

## 📋 Next Steps to Complete PyPI Publishing

### Option 1: Configure Trusted Publishing (Recommended)

**This is the most secure and automated approach.**

#### Step 1: Configure Test PyPI Trusted Publishing

1. Go to https://test.pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in the form:
   - **PyPI Project Name**: `pyodbc-mcp-server`
   - **Owner**: `jjones-wps`
   - **Repository name**: `pyodbc-mcp-server`
   - **Workflow name**: `release.yml`
   - **Environment name**: `test-pypi`
4. Click "Add"

#### Step 2: Configure Production PyPI Trusted Publishing

1. Go to https://pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in the form:
   - **PyPI Project Name**: `pyodbc-mcp-server`
   - **Owner**: `jjones-wps`
   - **Repository name**: `pyodbc-mcp-server`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Click "Add"

#### Step 3: Re-trigger the Workflow

Since the workflow has already run for v0.4.0, you need to trigger it again:

**Option A: Delete and recreate the tag** (triggers workflow automatically)
```bash
# Delete remote tag
git push origin :refs/tags/v0.4.0

# Delete local tag
git tag -d v0.4.0

# Recreate tag
git tag -a v0.4.0 -m "Release v0.4.0: Production Readiness"

# Push tag
git push origin v0.4.0
```

**Option B: Create a patch release** (if you want to avoid deleting the tag)
```bash
# Make a trivial change (e.g., update RELEASE_STATUS.md)
# Commit and push

# Bump version to 0.4.1
# Create new tag
git tag -a v0.4.1 -m "Release v0.4.1: Minor updates"
git push origin v0.4.1
```

#### Step 4: Verify Publication

After the workflow completes successfully:
- Test PyPI: https://test.pypi.org/project/pyodbc-mcp-server/
- Production PyPI: https://pypi.org/project/pyodbc-mcp-server/

---

### Option 2: Manual Upload with API Tokens (Less Secure)

**Only use this if you cannot configure trusted publishing.**

#### Prerequisites
- API tokens from SECURITY_MITIGATION_COMPLETE.md need to be revoked and regenerated
- New tokens must be added to GitHub Secrets

#### Steps

1. **Generate New Tokens**:
   - Test PyPI: https://test.pypi.org/manage/account/token/
   - Production PyPI: https://pypi.org/manage/account/token/

2. **Test Upload** (from local machine):
   ```bash
   source .venv/bin/activate
   python -m twine upload --repository testpypi dist/*
   # Enter Test PyPI token when prompted
   ```

3. **Verify Test PyPI**:
   - Check https://test.pypi.org/project/pyodbc-mcp-server/

4. **Production Upload**:
   ```bash
   python -m twine upload dist/*
   # Enter Production PyPI token when prompted
   ```

5. **Verify Production PyPI**:
   - Check https://pypi.org/project/pyodbc-mcp-server/

---

### Option 3: Wait and Publish Later

The build artifacts are already attached to the GitHub release. You can:
- Download them from https://github.com/jjones-wps/pyodbc-mcp-server/releases/tag/v0.4.0
- Upload to PyPI manually whenever ready
- Use the local `dist/` directory files

---

## 🎯 Recommendation

**Use Option 1: Configure Trusted Publishing**

Why?
- ✅ Most secure (no API tokens)
- ✅ Automated (runs on every tag push)
- ✅ No manual steps after initial setup
- ✅ Industry best practice
- ✅ Easy to audit and revoke

The one-time setup (5 minutes) is worth the long-term security and automation benefits.

---

## 📊 Current Release Status Summary

| Item | Status | Details |
|------|--------|---------|
| GitHub Tag | ✅ | v0.4.0 created and pushed |
| GitHub Release | ✅ | Created with comprehensive notes |
| Build Artifacts | ✅ | Attached to GitHub release |
| CHANGELOG | ✅ | Updated with v0.4.0 entry |
| Version Bump | ✅ | pyproject.toml updated to 0.4.0 |
| Workflow Updated | ✅ | PyPI publishing jobs added |
| Test PyPI | ⏳ | Awaiting trusted publishing config |
| Production PyPI | ⏳ | Awaiting trusted publishing config |

---

## 🔗 Useful Links

- **GitHub Release**: https://github.com/jjones-wps/pyodbc-mcp-server/releases/tag/v0.4.0
- **Workflow File**: `.github/workflows/release.yml`
- **Trusted Publishing Guide**: https://docs.pypi.org/trusted-publishers/
- **Test PyPI Publisher Setup**: https://test.pypi.org/manage/account/publishing/
- **Production PyPI Publisher Setup**: https://pypi.org/manage/account/publishing/

---

**Last Updated**: 2026-01-03
**Next Action**: Configure GitHub trusted publishing on PyPI and Test PyPI
