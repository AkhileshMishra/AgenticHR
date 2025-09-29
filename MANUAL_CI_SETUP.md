# Manual CI/CD Workflow Setup Guide

## Overview
Due to GitHub App permissions restrictions, the CI/CD workflow file needs to be manually added to the repository. Follow these steps to complete the setup.

## Steps to Add CI/CD Workflow

### Option 1: Using GitHub Web Interface (Recommended)

1. **Navigate to your repository**
   - Go to https://github.com/AkhileshMishra/AgenticHR

2. **Create the workflow directory**
   - Click "Create new file"
   - In the filename field, type: `.github/workflows/ci.yml`
   - GitHub will automatically create the directories

3. **Copy the workflow content**
   - Copy the entire content from the "CI Workflow File Content" section below
   - Paste it into the file editor

4. **Commit the file**
   - Scroll down to "Commit new file"
   - Add commit message: "Add CI/CD workflow for AgenticHR platform"
   - Add description: "Comprehensive CI/CD pipeline with linting, testing, security scanning, and SBOM generation"
   - Click "Commit new file"

### Option 2: Using Git Command Line

1. **Clone/pull latest changes**
   ```bash
   git pull origin main
   ```

2. **Create the workflow directory**
   ```bash
   mkdir -p .github/workflows
   ```

3. **Create the workflow file**
   ```bash
   cat > .github/workflows/ci.yml << 'EOF'
   [Copy the content from "CI Workflow File Content" section below]
   EOF
   ```

4. **Commit and push**
   ```bash
   git add .github/workflows/ci.yml
   git commit -m "Add CI/CD workflow for AgenticHR platform"
   git push origin main
   ```

### Option 3: Using GitHub CLI

1. **Create the file locally**
   ```bash
   mkdir -p .github/workflows
   # Copy the content to .github/workflows/ci.yml
   ```

2. **Push using GitHub CLI**
   ```bash
   gh repo sync
   git add .github/workflows/ci.yml
   git commit -m "Add CI/CD workflow for AgenticHR platform"
   git push origin main
   ```

## Verification

After adding the workflow file:

1. **Check Actions tab**
   - Go to the "Actions" tab in your GitHub repository
   - You should see the "ci" workflow listed

2. **Trigger a test run**
   - Make a small change to any file and push it
   - Or manually trigger the workflow from the Actions tab

3. **Monitor the workflow**
   - The workflow should run automatically on push/PR
   - Check that all jobs (lint-test-build, security) complete successfully

## Workflow Features

The CI/CD pipeline includes:

- **Linting**: Ruff code quality checks
- **Testing**: Pytest unit tests per service
- **Building**: Docker image builds for all services
- **Security**: Trivy filesystem and image vulnerability scanning
- **Compliance**: SBOM (Software Bill of Materials) generation
- **Artifacts**: SBOM uploaded as workflow artifact

## Troubleshooting

If you encounter issues:

1. **Workflow not appearing**: Ensure the file is in `.github/workflows/ci.yml` (exact path)
2. **Workflow failing**: Check the Actions tab for detailed error logs
3. **Permission issues**: Ensure you have write access to the repository
4. **Syntax errors**: Validate YAML syntax using online YAML validators

## Next Steps

Once the CI/CD workflow is successfully added:

1. All 6 checkboxes will be complete ✅
2. The platform will be ready for the next development phase (D-I)
3. Future commits will automatically trigger the CI/CD pipeline
4. Security scanning and SBOM generation will run on every push
