# PAWS AOL Example

This file demonstrates an AOL workflow adhering to the three mandatory sections (Provider, User Inputs, and Workflow Logic) using the **YAML format** specified in AOL v1.0.

> [!NOTE]
> AOL v1.0 uses YAML format for deterministic parsing and LLM generation reliability. See [AOL v1.0 Specification.md](./AOL%20v1.0%20Specification.md) for the complete schema.

## example.aol

```yaml
# Section 1: Provider Description
# Defines identity, access rights, and required profiles for the session.
provider:
  name: Localhost
  context:
    workspace: ./workspace
  entitlements:
    - scope: "Read/Write ./workspace/"
      capability: "Execute Bash Commands (Local)"

# Section 2: User Inputs
# Establishes "State Zero" for the Event Log.
user_inputs:
  prompt: "Show what date is today?"
  resources: []

# Section 3: Workflow Logic
# The execution script mapping steps to Extensions and defining data flow.
steps:
  - id: step_1
    description: Retrieve current system date
    extension: Bash
    tool: execute_command
    inputs:
      command: "date"
    outputs:
      stdout: "Current date string"

  - id: step_2
    description: Display the retrieved date
    extension: Bash
    tool: execute_command
    # The output from step_1 is fed as input into step_2
    inputs:
      command: "echo 'The current date is: {{step_1.stdout}}'"
    outputs:
      stdout: "Formatted date message"
```

## Breakdown of Compliance with Specifications

### Section 1 (Provider Description)
* **Specification:** Must define *who* the agent is and unlock credentials/capabilities.
* **Implementation:** Defined as `Localhost` provider with specific entitlements to execute local Bash commands, adhering to the "Entitlements" security model.

### Section 2 (User Inputs)
* **Specification:** Must define the raw prompt and initial assets to establish the initial state.
* **Implementation:** Captures the specific prompt ("Show what date is today?") and explicitly lists an empty resource list.

### Section 3 (Workflow Logic)
* **Specification:** Must contain sequential steps mapped to Extension/Tool definitions and allow for data chaining.
* **Implementation:**
  * **Step 1:** Calls the Bash extension's `execute_command` tool to get the date.
  * **Step 2:** Demonstrates **variable interpolation** using `{{step_1.stdout}}` to chain the output of step 1 into step 2.

---

## More Complex Example: Conditional Workflow

```yaml
provider:
  name: Localhost
  context: {}

user_inputs:
  prompt: "Check if a file exists and process it"
  resources:
    - ./data/input.csv

steps:
  - id: check_file
    description: Check if input file exists
    extension: Bash
    inputs:
      command: "test -f ./data/input.csv && echo 'exists' || echo 'missing'"
    outputs:
      stdout: "File status"

  - id: process_file
    description: Process the file if it exists
    extension: Python
    condition:
      if: "{{check_file.stdout}}" == "exists"
    inputs:
      script: process.py
      args:
        input: ./data/input.csv
    outputs:
      result: "Processing result"

  - id: report_missing
    description: Report if file is missing
    extension: Bash
    condition:
      if: "{{check_file.stdout}}" == "missing"
    inputs:
      command: "echo 'ERROR: Input file not found' >&2"
    on_failure:
      strategy: abort
```

---

*See [AOL v1.0 Specification.md](./AOL%20v1.0%20Specification.md) for complete schema documentation.*
