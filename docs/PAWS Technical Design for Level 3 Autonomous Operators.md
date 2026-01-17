This Technical Design Document (TDD) outlines the architecture for the **Progressive Autonomous Workflow Server (PAWS)**. This design is derived specifically from the requirements for a "Level 3 Autonomous Operator" as defined in *Three Levels of automation with generative AI* 1, 2, while incorporating architectural best practices from broader research on agentic systems, such as the *Architecture of Agency* and *OpenHands* frameworks.

# Technical Design: Progressive Autonomous Workflow Server (PAWS)

## 1. Executive Summary

PAWS is designed as a **Level 3 Autonomous Operator** system. Unlike Level 2 systems which rely on static workflows requiring user interaction at every step, PAWS functions as a proactive partner 3\. It receives a high-level intent and resources, independently formulates a plan using a descriptive "Autonomous Operator Language," and executes multi-step long-horizon tasks (e.g., generating a 5-minute video or a full illustrated book) with minimal human intervention.

## 2. System Architecture: The Agentic Loop

The core architecture follows a **recursive "Heartbeat Loop"** (Observe-Orient-Decide-Act) rather than a linear pipeline. The system is modular, ensuring clear boundaries between reasoning (Planner) and action (Executor).

### High-Level Data Flow

1. **User Input:** Prompt + Initial Resources.  
2. **Planner:** Generates a descriptive Workflow Plan (in Autonomous Operator Language).  
3. **Executor:** Parses the plan and orchestrates Extensions.  
4. **Extensions (Tools):** Interact with external APIs/environments (MCP-compatible).  
5. **Validator:** Verifies output against success criteria.  
6. **Feedback Loop:** If validation fails, the Planner refines the plan or the Executor retries.

## 3. Core Component Design

The system is composed of four mandatory components defined in the requirements 2, augmented by architectural resilience patterns.

### 3.1. Provider (Credential & Identity Management)

**Responsibility:** Manages authentication and authorization for external services.

* **Design:** A secure vault that stores pre-authorized credentials. It implements a "Secret Registry" pattern with auto-masking to prevent credential leakage in logs.  
* **Entitlements:** The Provider defines the "entitlements" of the agent, strictly scoping what the agent is authorized to do on behalf of the user (e.g., "read-only" vs. "execute").

### 3.2. Extensions (The Abstract Tool Layer)

* **Responsibility:** An abstraction layer for 3rd-party services (e.g., Google Gemini, ComfyUI, FFmpeg) 
* **Standardization:** All extensions must be compatible with the **Model Context Protocol (MCP)**. This ensures a standardized client-host architecture where tools are exposed to the agent via a uniform interface, regardless of the underlying API.  
* **Sandboxing:** Extensions execute within isolated environments (e.g., Docker containers) to prevent "shared fate" failures where a tool crash takes down the whole server.

### 3.3. Validator (The Critic)

**Responsibility:** Verifies extension output against a definition of success/failure.

* **Logic:** Implements the **Evaluator-Optimizer** pattern. For example, if an image generation extension produces a black image, the Validator flags the failure, preventing the workflow from proceeding to the next step (e.g., video synthesis) with bad data.  
* **Metrics:** Uses both deterministic checks (file size, format) and semantic checks (using a secondary LLM to verify relevance to the prompt).

### 3.4. Workflow Planner & Executor (The "Brain")

This component is split into two distinct sub-systems that share the same workflow language.

#### A. The Planner (Reasoning Engine)

* **Input:** User prompt and resources.  
* **Function:** Performs reasoning to decompose the request into a multi-step plan.  
* **Output:** A text file in **Autonomous Operator Language** (see Section 4). This acts as the "source of truth" for the execution.

#### B. The Executor (Runtime Engine)

* **Function:** Follows the instructions in the generated Workflow Plan. It handles the "Vision-Action Loop," calling extensions, waiting for processing, and retrieving outputs.  
* **State Management:** It maintains an **Event Log** (append-only) to track every action, observation, and state change. This ensures the workflow is reproducible and resumable if interrupted.

## 4. Data Design: Autonomous Operator Language

To meet the requirement for a "high-level, human-readable" language (not JSON/Code), PAWS utilizes a structured text format divided into three mandatory sections.

### Schema Definition

* **Section 1: Provider Description**  
* Defines which credentials and authenticated sessions are active.  
* **Section 2: User Inputs**  
* **Prompt:** The natural language request (e.g., "Create a children's book about...").  
* **Initial Resources:** Links to reference files, images, or style guides.  
* **Section 3: Workflow Logic**  
* **Descriptive Steps:** Sequential instructions (e.g., "Step 1: Generate character consistency sheet using ComfyUI Extension").  
* **Conditionals:** Logic switches based on Validator output (e.g., "IF validation fails THEN retry with seed+1") 2\.

## 5. Operational Workflow (Level 3 Autonomy)

This process demonstrates how PAWS achieves "Conditional Autonomy" acting independently but allowing for intervention.

* **Initialization:** User submits a request. The *Planner* generates the Workflow Plan text file.  
* **Execution Loop:**  
* The *Executor* reads the current step from the Plan.  
* It selects the appropriate *Extension* (e.g., calling LLM for text, ComfyUI for images) 4\.  
* **Action:** The Extension executes the task (e.g., generating 3 seconds of video).  
* **Validation:** The *Validator* checks the output.  
* **Iterative Refinement:**  
* If valid, the output (e.g., the last frame of the video) is fed as input into the next iteration 4\.  
* If invalid, the *Executor* triggers a self-correction loop defined in the Workflow Logic 5\.  
* **Completion:** The *Executor* merges artifacts (e.g., ffmpeg merge) and presents the final long-form asset.

## 6. Safety & Governance (Human-in-the-Loop)

While Level 3 implies the system resolves issues on its own, PAWS must include "interrupt" mechanisms for high-stakes decisions.

* **Escalation Protocol:** If the Validator detects repeated failures or low confidence scores, the system enters a **"User as Consultant" (Level 3)** state. The workflow pauses and requests human feedback before proceeding.  
* **Observability:** The system must emit real-time traces (via the Event Log) so the user can audit the "thought process" of the Planner.

## 7. Implementation Roadmap

* **Phase 1 (Core):** Build the Executor engine capable of parsing the text-based Autonomous Operator Language and invoking local MCP tools.  
* **Phase 2 (Reasoning):** Fine-tune the Planner (LLM) to reliably generate valid Workflow Plans from vague user prompts.  
* **Phase 3 (Persistence):** Implement the event-sourced state database to allow workflows to run for hours (e.g., video rendering) without data loss.

