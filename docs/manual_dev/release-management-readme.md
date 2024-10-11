1. Commit the changes you want.

2. Create a tag starting with v... (e.g., v1.0.1), taking care that you are on the relevant branch, example:
```
git tag v1.0.1
```

3. Push to the branch with:
```
git push origin v1.0.1
```

4. The package will automatically be compiled (currently with Python 3.10) and uploaded to releases. This happens because we have configured release.yml file in .github/workflows.

5. Remember that the version of the tag and the Python package version defined in pyproject.toml should be the same.