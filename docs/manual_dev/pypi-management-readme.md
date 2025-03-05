# Automatically publish a Python package to PyPI using GitHub Actions 

**Note**: We keep this instructions here in order to save this knowlage, but do not intend (for now) to publish the DyCoV tool in Pypi, because it is not a library but an application and it needs other non-python applications (Dynawo and Latex).

### Steps to configure automatic publishing to PyPI when you push a new commit to GitHub.

## 1. Configure `pyproject.toml`

Make sure you have the `pyproject.toml` file to define your package configuration:

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "your_package"
version = "0.1.0"
description = "Description of your package"
readme = "README.md"
license = { text = "MIT" }
authors = [
    { name = "Your Name", email = "your_email@example.com" }
]
dependencies = [
    "numpy >= 1.18.0",
    "requests >= 2.23.0"
]

[project.urls]
"Homepage" = "https://github.com/your_username/your_repository"
```

## 2. Set up a PyPI Token

1. Log in to your [PyPI](https://pypi.org/) account.
2. Go to **Account Settings** and navigate to **API Tokens**.
3. Create a new API token and copy it.

## 3. Store the PyPI Token in GitHub Secrets

1. Go to your repository on GitHub.
2. Click on **Settings** > **Secrets and variables** > **Actions**.
3. Add a new secret with the name `PYPI_TOKEN` and paste the token from PyPI.

## 4. Create a GitHub Actions Workflow

1. In your project, create the following directory and file:
   - Directory: `.github/workflows`
   - File: `publish.yml`

2. Inside `publish.yml`, add the following workflow:

```yaml
name: Publish Python Package

on:
  push:
        tags:
      - 'v*'  # Triggered when you push a tag that starts with 'v', such as v1.0.0

jobs:
  publish:
    runs-on: ubuntu-latest

    steps:
      - name: Check out the repository
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.x'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build the package
        run: python -m build

      - name: Publish package to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: python -m twine upload dist/*
```


## 5. Create a Tag to Trigger the Workflow

To trigger the workflow and publish to PyPI, create a tag in your repository:

```bash
git tag v1.0.0
git push origin v1.0.0
```