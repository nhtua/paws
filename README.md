# PAWS PoC Walkthrough

This Proof of Concept implements the Planner (Gemini-powered) and Executor (Localhost/Bash) for PAWS.

## Setup

1.  **Install Dependencies**:
    Dependencies are managed with `uv`.
    ```bash
    uv sync
    ```

2.  **Configuration**:
    Copy `.env.example` to `.env` and add your Google Gemini API key.
    ```bash
    cp .env.example .env
    # Edit .env and set GEMINI_API_KEY
    ```

## Usage

### 1. Planner (Generate AOL)
The Planner takes a prompt and generates an `.aol` file (YAML format).

```bash
uv run python -m paws.planner "Get today's date using bash" workflow.aol
```

This will create `workflow.aol`.

### 2. Executor (Run AOL)
The Executor reads the `.aol` file (YAML) and executes the steps using the Localhost provider and extensions.

```bash
uv run python -m paws.executor workflow.aol
```

## Verification
You can run the manual test file to verify the Executor without an API key:

```bash
uv run python -m paws.executor manual_test.aol
```

## Components Implemented
- **models.py**: Core data structures (AOLWorkflow, AOLStep, etc.).
- **registry.py**: Extension registry (auto-discovers Bash).
- **extensions/bash.py**: MCP-compliant Bash extension.
- **planner.py**: Generates AOL using Gemini.
- **executor.py**: Executes AOL steps via MCP tools.
