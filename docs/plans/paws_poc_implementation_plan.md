# PAWS PoC Implementation Plan

## Goal
Implement a Minimum Viable Proof of Concept (PoC) for PAWS (Progressive Autonomous Workflow Server), comprising the Planner, Executor, and a basic AOL (Autonomous Operator Language) structure with a Localhost/Bash extension.

## Proposed Changes

### Dependencies
- Add `google-genai` for Gemini API access.
- Add `python-dotenv` for loading `GEMINI_API_KEY`.
- Add `pydantic` for data validation.
- Add `pyyaml` for AOL parsing.

### Structure
Files will be organized in `paws/` directory.

#### [NEW] `paws/core/models.py`
- Define AOL data structures (Pydantic models).
    - `AOLProvider`: Provider context.
    - `AOLUserInputs`: User prompt and resources.
    - `AOLExtension`: Definition of the extension to be used.
    - `AOLStep`: Workflow steps, including:
        - `extension`: The `AOLExtension` to use.
        - `inputs`: Input parameters for the tool.
        - `outputs`: Expected output definition.
    - `AOLWorkflow`: Complete AOL structure.

#### [NEW] `paws/core/registry.py`
- Class `Registry`.
- Method `discover_extensions() -> List[AOLExtension]`: Returns list of available extensions (mocked or local scan for PoC).
- Method `get_extension(name: str) -> AOLExtension`: Resolves extension details.
- Acts as the source of truth for what tools the Planner can use.

#### [NEW] `paws/planner.py`
- Class `Planner`.
- Method `plan(prompt: str) -> AOLWorkflow`.
- **Update**: Auto-discovers available extensions from `Registry` to include in the LLM system prompt context.
- Uses Gemini API to generate AOL content from prompt.
- Function `save_aol(aol: AOLWorkflow, path: str)`.
- CLI entry point: `python -m paws.planner <prompt> <output_path>`

#### [NEW] `paws/executor.py`
- Class `Executor`.
- Method `execute(aol_path: str)`.
- Parses AOL file.
- **Update**: Uses `Registry` or AOL metadata to resolve and initiate required MCP extensions.
- Implements `Localhost` provider logic, including managing user context (username/password) if required by the provider definition.
- Implements execution loop (OODA loop).
- Strict MCP Client implementation: Sends JSON-RPC `call_tool` messages to extensions.
- CLI entry point: `python -m paws.executor <aol_path>`

#### [NEW] `paws/extensions/bash.py`
- `BashExtension` class (acting as an MCP Server).
- Implements MCP Protocol for `call_tool`.
- Accepts JSON-RPC requests.
- Executes commands (e.g., via subprocess) but interacts *only* via valid MCP payloads.
- Returns MCP-compliant JSON responses.

### AOL Format
We use **YAML** as the structured format for AOL files.

## Verification Plan

### Automated Tests
1.  **Unit Tests**:
    - Test AOL parsing schema.
    - Test Bash extension with simple echo command.
2.  **Integration Test**:
    - Workflow:
        1.  Run Planner with "What is the date today?".
        2.  Verify `.aol` file is created.
        3.  Run Executor with the generated `.aol`.
        4.  Verify output contains the date.

### Manual Verification
1.  Set `GEMINI_API_KEY` in `.env`.
2.  Run: `python -m paws.planner "Get the current date using bash" test.aol`
3.  Check `test.aol` content (YAML).
4.  Run: `python -m paws.executor test.aol`
5.  Check console output.
