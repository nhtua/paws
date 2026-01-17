# Autonomous Operator Language (AOL) v1.0 Specification

**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2026-01-17

---

## 1. Introduction

The **Autonomous Operator Language (AOL)** is a Domain-Specific Language (DSL) designed as the intermediate representation between the PAWS Planner (an LLM-powered reasoning engine) and the PAWS Executor (a deterministic runtime engine).

### 1.1 Design Principles

| Principle | Description |
|-----------|-------------|
| **Human-Readable** | Auditable and modifiable by humans |
| **Deterministic Parsing** | The Executor maps steps to functions without LLM interpretation |
| **Verifiable** | Supports semantic validation after each step |
| **Resumable** | Enables event sourcing for crash recovery |
| **LLM-Friendly** | Optimized for generation by frontier LLMs |

### 1.2 Why YAML?

AOL v1.0 uses **YAML 1.2** as its serialization format because:
- Deterministic, well-defined parsing semantics
- Excellent tooling for validation (JSON Schema compatibility)
- LLMs generate valid YAML more reliably than custom DSLs
- Human-readable while remaining machine-parsable

---

## 2. File Format

| Property | Value |
|----------|-------|
| **Extension** | `.aol` |
| **Encoding** | UTF-8 |
| **YAML Version** | 1.2 |

### 2.1 Document Structure

An AOL file consists of **three mandatory sections**:

```yaml
# Section 1: Provider Description
provider:
  # ... provider configuration

# Section 2: User Inputs
user_inputs:
  # ... original request and resources

# Section 3: Workflow Logic
steps:
  # ... execution steps
```

---

## 3. Section 1: Provider Description

The Provider section defines identity, access rights, and required capabilities for the workflow session.

### 3.1 Schema

```yaml
provider:
  name: <string>           # Required: Provider identifier
  context: <object>        # Optional: Environment/auth context
  entitlements:            # Optional: Access control rules
    - scope: <string>      # Resource scope (e.g., "Read/Write ./workspace/")
      capability: <string> # Allowed action (e.g., "Execute Bash Commands")
```

### 3.2 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Provider identifier (e.g., "Localhost", "Remote-GPU-Cluster") |
| `context` | object | No | Key-value pairs for authentication, environment variables, or session configuration |
| `entitlements` | array | No | List of access control rules defining what the workflow can access |

### 3.3 Example

```yaml
provider:
  name: Localhost
  context:
    workspace: /home/user/projects/video-gen
    max_retries: 3
  entitlements:
    - scope: "Read/Write ./workspace/"
      capability: "Execute Bash Commands (Local)"
    - scope: "Read ./assets/"
      capability: "File Access"
```

---

## 4. Section 2: User Inputs

The User Inputs section establishes "State Zero" for the Event Log—the initial state before any execution.

### 4.1 Schema

```yaml
user_inputs:
  prompt: <string>         # Required: Original user request
  resources: <array>       # Optional: Initial file paths or URIs
```

### 4.2 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | The original natural language request from the user |
| `resources` | array of strings | No | File paths, URLs, or URIs to initial assets |

### 4.3 Example

```yaml
user_inputs:
  prompt: "Create a short video about climate change with narration"
  resources:
    - ./assets/background_music.mp3
    - ./assets/stock_footage/nature.mp4
```

---

## 5. Section 3: Workflow Logic (Steps)

The Steps section contains the **linear, sequential execution plan** with optional control flow.

### 5.0 Execution Model: Linear Flow

> [!IMPORTANT]
> **Steps execute in declaration order.** The order of steps in the YAML array defines the execution sequence—step N always runs before step N+1 (unless skipped by a condition). This linear model is fundamental to AOL and enables:
> - Predictable execution order
> - Safe variable interpolation (steps can only reference *previous* step outputs)
> - Deterministic resumability after crashes

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Step 1  │───▶│ Step 2  │───▶│ Step 3  │───▶│ Step N  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                    │
                    ▼ (condition: false)
                 [SKIP]
```

### 5.1 Step Schema

```yaml
steps:
  - id: <string>               # Required: Unique step identifier
    description: <string>      # Required: Human-readable description
    extension: <string>        # Required: Target extension name
    tool: <string>             # Optional: Specific tool/capability (defaults to extension's primary tool)
    inputs: <object>           # Required: Arguments for the tool
    outputs: <object>          # Optional: Expected output schema
    condition: <condition>     # Optional: Conditional execution
    on_failure: <failure>      # Optional: Error handling strategy
    timeout: <duration>        # Optional: Maximum execution time
```

### 5.2 Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (e.g., "step_1", "generate_script") |
| `description` | string | Yes | Human-readable explanation of what this step does |
| `extension` | string | Yes | Name of the extension to invoke (must be registered) |
| `tool` | string | No | Specific capability within the extension |
| `inputs` | object | Yes | Key-value arguments passed to the tool |
| `outputs` | object | No | Schema describing expected output keys |
| `timeout` | string | No | Max duration (e.g., "30s", "5m", "1h") |

### 5.3 Example: Basic Step

```yaml
steps:
  - id: step_1
    description: Get current system date
    extension: Bash
    tool: execute_command
    inputs:
      command: "date '+%Y-%m-%d'"
    outputs:
      stdout: "Current date in ISO format"
```

---

## 6. Variable Interpolation

Steps can reference outputs from previous steps using interpolation syntax.

### 6.1 Syntax

```
{{<step_id>.<output_key>}}
```

### 6.2 Built-in Variables

| Variable | Description |
|----------|-------------|
| `{{step_id.stdout}}` | Standard output from a step |
| `{{step_id.stderr}}` | Standard error from a step |
| `{{step_id.exit_code}}` | Exit code from a step |
| `{{step_id.result}}` | Full result object from a step |
| `{{user_inputs.prompt}}` | Original user prompt |
| `{{provider.name}}` | Provider name |

### 6.3 Example: Chaining Outputs

```yaml
steps:
  - id: get_date
    description: Get current date
    extension: Bash
    inputs:
      command: "date '+%Y-%m-%d'"
    outputs:
      stdout: "Date string"

  - id: create_file
    description: Create file with today's date
    extension: Bash
    inputs:
      command: "echo 'Report generated on {{get_date.stdout}}' > report.txt"
```

---

## 7. Control Flow

AOL v1.0 supports conditional execution and branching to handle dynamic workflows.

### 7.1 Conditional Execution (`condition`)

A step executes only if its condition evaluates to `true`.

#### Syntax

```yaml
condition:
  if: <expression>           # Boolean expression
```

#### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equals | `"{{step_1.exit_code}}" == "0"` |
| `!=` | Not equals | `"{{step_1.stdout}}" != ""` |
| `>`, `>=`, `<`, `<=` | Numeric comparison | `"{{step_1.score}}" >= "0.8"` |
| `contains` | String contains | `"{{step_1.stdout}}" contains "success"` |
| `not` | Logical negation | `not "{{step_1.stdout}}" contains "error"` |
| `and`, `or` | Logical operators | `"{{a.x}}" == "1" and "{{b.y}}" == "2"` |

#### Example

```yaml
steps:
  - id: check_file
    description: Check if output file exists
    extension: Bash
    inputs:
      command: "test -f output.mp4 && echo 'exists' || echo 'missing'"
    outputs:
      stdout: "File status"

  - id: generate_video
    description: Generate video only if missing
    extension: ComfyUI
    condition:
      if: "{{check_file.stdout}}" == "missing"
    inputs:
      workflow: video_generation.json
```

### 7.2 Switch/Case (`switch`)

For multi-branch decisions based on a single value.

#### Syntax

```yaml
switch:
  value: <expression>        # Value to match against
  cases:
    - match: <value>         # Literal value to match
      steps: [<step_ids>]    # Steps to execute if matched
    - match: <value>
      steps: [<step_ids>]
  default: [<step_ids>]      # Optional: Steps if no match
```

#### Example

```yaml
steps:
  - id: detect_format
    description: Detect input file format
    extension: Bash
    inputs:
      command: "file --mime-type -b input.file"
    outputs:
      stdout: "MIME type"

  - id: process_routing
    description: Route to appropriate processor
    switch:
      value: "{{detect_format.stdout}}"
      cases:
        - match: "video/mp4"
          steps: [process_video]
        - match: "image/png"
          steps: [process_image]
        - match: "audio/mpeg"
          steps: [process_audio]
      default: [handle_unknown_format]

  - id: process_video
    description: Process video file
    extension: FFmpeg
    condition:
      if: false  # Controlled by switch
    inputs:
      operation: transcode

  # ... other processor steps
```

### 7.3 Loops (`loop_begin` / `loop_end`)

Loops allow repeating a sequence of steps until an exit condition is met. Loops are defined using **marker steps** that bracket the loop body.

#### Syntax

A loop consists of:
1. **`loop_begin`** step: Marks the start of the loop with a built-in counter
2. **Loop body**: One or more regular steps
3. **`loop_end`** step: Contains the exit condition that determines whether to continue or break

```yaml
steps:
  # Loop start marker
  - id: <loop_id>
    loop_begin:
      max_iterations: <number>    # Optional: Safety limit (default: 100)

  # Loop body steps...
  - id: <step_in_loop>
    extension: <extension>
    inputs: { ... }

  # Loop end marker with exit condition
  - id: <loop_id>_end
    loop_end:
      loop_id: <loop_id>          # Required: References the loop_begin step
      exit_when: <expression>     # Required: Exit condition (true = exit loop)
```

#### Built-in Counter

Each `loop_begin` has an automatic **counter** property that:
- Starts at `0` on first entry
- Increments by `1` every time the flow passes through `loop_begin` (including loop-backs)
- Is accessible via `{{<loop_id>.counter}}`

| Variable | Description |
|----------|-------------|
| `{{loop_id.counter}}` | Current iteration count (0-indexed on first pass) |

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `loop_begin.max_iterations` | integer | No | Maximum iterations before forced exit (default: 100). **Set to `0` to disable limit.** |
| `loop_end.loop_id` | string | Yes | ID of the corresponding `loop_begin` step |
| `loop_end.exit_when` | expression | Yes | Boolean expression; when `true`, exit the loop |

#### Execution Semantics

```
┌──────────────────────────────────────────────────────────────┐
│  1. Flow reaches loop_begin                                  │
│     → counter++ (incremented BEFORE body executes)           │
│     → If max_iterations > 0 AND counter > max_iterations:    │
│         FORCED EXIT with warning                             │
│                                                              │
│  2. Execute loop body steps linearly                         │
│                                                              │
│  3. Flow reaches loop_end                                    │
│     → Evaluate exit_when expression                          │
│     → If true: EXIT loop, continue to next step              │
│     → If false: JUMP BACK to loop_begin (step 1)             │
└──────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> The loop **always exits** when `counter > max_iterations`, even if `exit_when` evaluates to `false`. This is a safety mechanism to prevent infinite loops.
>
> **Exception:** When `max_iterations = 0`, the iteration limit check is disabled and only `exit_when` controls loop termination. Use with caution—ensure your `exit_when` condition will eventually become true.

#### Example: Retry Until Success

```yaml
steps:
  - id: retry_loop
    loop_begin:
      max_iterations: 5

  - id: attempt_api_call
    description: Try to call external API
    extension: HTTP
    inputs:
      method: POST
      url: "https://api.example.com/process"
      body: "{{user_inputs.prompt}}"
    outputs:
      status_code: "HTTP status code"
      response: "API response body"
    on_failure:
      strategy: skip  # Don't abort, let loop handle retry

  - id: check_success
    description: Check if API call succeeded
    extension: Bash
    inputs:
      command: |
        if [ "{{attempt_api_call.status_code}}" = "200" ]; then
          echo "success"
        else
          echo "failure"
        fi
    outputs:
      stdout: "success or failure"

  - id: retry_loop_end
    loop_end:
      loop_id: retry_loop
      exit_when: "{{check_success.stdout}}" == "success"
```

#### Example: Process Items in a List

This example uses the **built-in counter** `{{process_loop.counter}}` instead of manually managing a counter step:

```yaml
steps:
  - id: get_total_items
    description: Count items to process
    extension: Bash
    inputs:
      command: "ls ./items/ | wc -l"
    outputs:
      stdout: "Total item count"

  - id: process_loop
    loop_begin:
      max_iterations: 1000

  - id: get_current_item
    description: Get item at current index (using built-in counter)
    extension: Bash
    inputs:
      # counter is 1 on first iteration, 2 on second, etc.
      command: "ls ./items/ | sed -n '{{process_loop.counter}}p'"
    outputs:
      stdout: "Current item filename"

  - id: process_item
    description: Process the current item
    extension: Python
    inputs:
      script: process.py
      args:
        file: "./items/{{get_current_item.stdout}}"

  - id: process_loop_end
    loop_end:
      loop_id: process_loop
      # Exit when counter exceeds total items
      exit_when: "{{process_loop.counter}}" >= "{{get_total_items.stdout}}"
```

#### Nested Loops

Loops can be nested. Each loop must have a unique `id` and its `loop_end` must reference the correct `loop_id`.

```yaml
steps:
  - id: outer_loop
    loop_begin:
      max_iterations: 10

  - id: inner_loop
    loop_begin:
      max_iterations: 5

  # Inner loop body...

  - id: inner_loop_end
    loop_end:
      loop_id: inner_loop
      exit_when: <inner_condition>

  # More outer loop steps...

  - id: outer_loop_end
    loop_end:
      loop_id: outer_loop
      exit_when: <outer_condition>
```

> [!WARNING]
> **Loop Validation Rules**:
> - Every `loop_begin` MUST have a matching `loop_end` with the same `loop_id`
> - `loop_end` must appear AFTER its corresponding `loop_begin`
> - Nested loops must be properly nested (no interleaving)
> - `exit_when` can only reference steps within the loop body or before the loop

---

## 8. Error Handling (`on_failure`)

Define behavior when a step fails validation or execution.

### 8.1 Syntax

```yaml
on_failure:
  strategy: <strategy>       # Required: How to handle failure
  max_retries: <number>      # Optional: Max retry attempts (for "retry" strategy)
  fallback_step: <step_id>   # Optional: Step to execute (for "fallback" strategy)
```

### 8.2 Strategies

| Strategy | Description |
|----------|-------------|
| `abort` | Stop workflow execution immediately (default) |
| `retry` | Retry the step up to `max_retries` times |
| `skip` | Log the failure and continue to next step |
| `fallback` | Execute `fallback_step` instead |
| `self_heal` | Trigger Planner feedback loop for plan regeneration |

### 8.3 Example

```yaml
steps:
  - id: generate_image
    description: Generate image with AI
    extension: ComfyUI
    inputs:
      workflow: image_gen.json
      prompt: "A serene mountain landscape"
    outputs:
      image_path: "Path to generated image"
    on_failure:
      strategy: retry
      max_retries: 3

  - id: upload_image
    description: Upload to cloud storage
    extension: AWS
    inputs:
      action: s3_upload
      file: "{{generate_image.image_path}}"
    on_failure:
      strategy: fallback
      fallback_step: save_locally
```

---

## 9. Validation Rules

### 9.1 Schema Validation

The Executor MUST validate AOL files against these rules before execution:

| Rule | Description |
|------|-------------|
| **Required Sections** | `provider`, `user_inputs`, and `steps` must all be present |
| **Unique Step IDs** | All step `id` values must be unique within the workflow |
| **Extension Exists** | Each `extension` must be registered in the Extension Registry |
| **Valid References** | Variable interpolations must reference existing step IDs and output keys |
| **Acyclic References** | Steps can only reference outputs from *previous* steps |

### 9.2 Semantic Validation (Runtime)

After each step execution, the Executor SHOULD validate:

| Check | Description |
|-------|-------------|
| **Output Exists** | Expected output files/values are present |
| **Type Match** | Output types match expected schema |
| **Non-Empty** | Critical outputs are non-null and non-empty |

---

## 10. Complete Example

```yaml
# AOL v1.0 Example: Generate and Process a Report

provider:
  name: Localhost
  context:
    workspace: ./workspace
  entitlements:
    - scope: "Read/Write ./workspace/"
      capability: "Execute Bash Commands"
    - scope: "Execute"
      capability: "Python Scripts"

user_inputs:
  prompt: "Generate a sales report for Q4 2025"
  resources:
    - ./data/sales_q4_2025.csv

steps:
  - id: validate_data
    description: Validate input CSV file exists and is readable
    extension: Bash
    inputs:
      command: "test -r ./data/sales_q4_2025.csv && echo 'valid' || echo 'invalid'"
    outputs:
      stdout: "Validation result"

  - id: generate_report
    description: Generate report from CSV data
    extension: Python
    condition:
      if: "{{validate_data.stdout}}" == "valid"
    inputs:
      script: generate_report.py
      args:
        input: ./data/sales_q4_2025.csv
        output: ./workspace/report.pdf
    outputs:
      report_path: "Path to generated PDF"
    on_failure:
      strategy: retry
      max_retries: 2

  - id: notify_completion
    description: Print completion message
    extension: Bash
    inputs:
      command: "echo 'Report generated: {{generate_report.report_path}}'"

  - id: handle_invalid_data
    description: Handle missing or invalid input file
    extension: Bash
    condition:
      if: "{{validate_data.stdout}}" == "invalid"
    inputs:
      command: "echo 'ERROR: Input data file is missing or unreadable' >&2 && exit 1"
    on_failure:
      strategy: abort
```

---

## 11. Reserved Keywords

The following keywords are reserved for future AOL versions:

| Keyword | Reserved For |
|---------|--------------|
| `parallel` | Concurrent step execution |
| `import` | Workflow composition |
| `try`/`catch` | Advanced error handling |
| `variables` | Workflow-level variable declarations |
| `break` | Early loop exit without condition |
| `continue` | Skip to next loop iteration |

---

## Appendix A: JSON Schema

A formal JSON Schema for AOL v1.0 validation is available at:  
`schemas/aol-v1.0.schema.json` (to be implemented)

---

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-17 | Initial specification with linear execution, conditions, switch/case, loops, and error handling |

