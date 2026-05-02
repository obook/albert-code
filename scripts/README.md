# Project Management Scripts

This directory contains scripts that support project versioning and deployment workflows.

## Versioning

### Usage

```bash
# Bump major version (1.0.0 -> 2.0.0)
python3 scripts/bump_version.py major

# Bump minor version (1.0.0 -> 1.1.0)
python3 scripts/bump_version.py minor

# Bump patch/micro version (1.0.0 -> 1.0.1)
python3 scripts/bump_version.py micro
# or
python3 scripts/bump_version.py patch
```
