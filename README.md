# ZODC Service Integration

This is the service integration for ZODC.

## Requirements

- Python 3.12
- Poetry
- Docker
- Docker Compose

## Installation

```bash
poetry install
```

## Running the service

```bash
python -m src.main
```

## Linting

### Ruff check

```bash
ruff check src --fix
```

### MyPy

```bash
mypy src --show-traceback --explicit-package-base
```

# To do

- Fix bug when link project, project id is null in db after inserted
