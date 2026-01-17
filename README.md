![PAWS Mascot - A cute golden puppy](docs/PAWS-mascot.png)

# PAWS - Progressive Autonomous Workflow System 🐾

**PAWS** is an autonomous workflow execution system that decouples *reasoning* from *action*. Instead of a single AI agent loop that continuously queries an LLM, PAWS splits the process into two distinct phases:

1. **Planning** — An LLM "compiles" user intent into a static, verifiable plan
2. **Execution** — A deterministic engine executes that plan using a robust runtime environment

The bridge between these phases is the **Autonomous Operator Language (AOL)**, a human-readable Domain-Specific Language that serves as the system's "source of truth."

---

## 🚀 Why PAWS?

Most generative AI tools today only offer the ability to generate small, short-form content — a single photo, an 8-second video, a short essay. When it comes to **long-form content** like illustrated books, 5-minute videos, or lengthy novels, current tools struggle with maintaining relevant content, character identity, and logical coherence.

PAWS addresses this by providing:

- **Level 3 Autonomy** — Minimum human interaction for complex, multi-step tasks
- **Reproducible Workflows** — Plans are text files that can be shared and re-executed
- **Deterministic Execution** — No "token snowball" — the executor is a state machine, not an AI
- **MCP-Compatible Extensions** — Easily integrate with third-party tools and AI agents

---

## 🏗️ Core Architecture

| Component | Description |
|-----------|-------------|
| **Planner** | LLM-powered "compiler" that converts natural language prompts into AOL workflows |
| **Executor** | Deterministic runtime engine that parses and executes AOL files step-by-step |
| **AOL** | Domain-Specific Language bridging reasoning and action — human-readable and machine-parseable |
| **Extensions** | MCP-compliant tools (e.g., Bash, ComfyUI, FFmpeg) that perform actual work |
| **Providers** | Manage authentication and credentials for extensions |
| **Validators** | Optional components that verify extension outputs meet success criteria |

---

## 📚 Design Documentation

For detailed technical specifications and architectural decisions, see the design documents in [`docs/designs/`](docs/designs/):

| Document | Description |
|----------|-------------|
| [**Three Levels of Automation**](docs/designs/PAWS%20Three%20levels%20of%20automation%20with%20generative%20AI.md) | Vision document explaining the three automation levels and why Level 3 autonomy matters |
| [**Core Architecture**](docs/designs/PAWS%20Core%20Architecture_%20The%20Planner%20and%20Executor%20Framework.md) | Deep dive into the Planner, Executor, and AOL specification |
| [**Phase 1 Technical Design**](docs/designs/PAWS%20Phase%201%20Technical%20Design_%20Core%20Execution%20and%20Extension%20Architecture.md) | Implementation details for core execution and extension architecture |
| [**Level 3 Operators**](docs/designs/PAWS%20Technical%20Design%20for%20Level%203%20Autonomous%20Operators.md) | Technical design for autonomous operators |

---

## 🎯 Example Use Cases

- **Illustrated Books** — "Create an illustration book with many color pages for the story Goldilocks and Three Bears" → PAWS generates 23 pages over 2 hours
- **Long-Form Video** — "Generate a video of a vlogger reviewing a phone following this script..." → PAWS creates a 5-minute video over 10 hours, maintaining character consistency frame-by-frame

---

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
