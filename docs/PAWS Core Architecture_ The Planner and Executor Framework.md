Based on the expanded sources, specifically the PAWS Phase 1 technical design, OpenHands architecture, and agentic design principles, I have updated the technical introduction document.  
This version now explicitly details the architecture of the **Planner** (the "Compiler") and provides a deep dive into the **Executor** (the "Runtime Engine"), explaining how it manages state, isolation, and the "Agent-Computer Interface" without constant LLM dependency.

# Technical Specification: PAWS Core Architecture & AOL

**Version:** 1.1**System Context:** Progressive Autonomous Workflow Server (PAWS)**Core Components:** Planner (Compiler), AOL (Bytecode), Executor (Runtime)

## 1. Executive Summary

The PAWS architecture fundamentally decouples **reasoning** from **action**. Instead of a single "Agent" loop that continuously queries an LLM for what to do next, PAWS splits the lifecycle into two distinct phases:

1. **Planning:** An LLM "compiles" user intent into a static, verifiable plan.  
2. **Execution:** A deterministic engine executes that plan using a robust runtime environment.

The bridge between these two phases is the **Autonomous Operator Language (AOL)**, a high-level Domain-Specific Language (DSL) that serves as the system's "source of truth".

## 2. The Planner: The Reasoning Engine ("The Compiler")

The Planner is the entry point of the system. Its implementation is lightweight because it offloads the heavy cognitive lifting to frontier reasoning models (e.g., o1, Claude 3.5 Sonnet, DeepSeek R1).

* **Role:** The Planner functions as a **Compiler**. It takes a vague natural language prompt (High-Level Intent) and "compiles" it into a strict, executable AOL file.  
* **Self-Completion:** The Planner must hallucinate (predict) necessary details that the user omitted. For example, if the user says "Make a video," the Planner infers the need for a script, a voiceover, and specific visual assets, encoding these as explicit steps in the AOL file.  
* **Output:** A static text file (e.g., workflow_001.aol) that contains all decision logic, resource paths, and tool parameters required for the task.

## 3. The Executor: The Runtime Engine

*Implementation Difficulty: High*  
The Executor is the most complex component of the PAWS system. It is **not** an AI agent; it is a **deterministic state machine** written in code (Python). It is responsible for parsing the AOL file, managing the environment, and enforcing safety.

### 3.1. Design Philosophy: The "Virtual Machine"

The Executor acts as a Virtual Machine (VM) for AOL. It does not "understand" the plan; it parses and routes instructions.

1. **Deterministic Parsing:** The Executor reads Step 1: Generate image and maps it directly to a specific function call. It does not need to ask an LLM "What should I do with Step 1?".  
2. **The "Heartbeat" Loop:** The Executor runs on a recursive **Observe-Orient-Decide-Act (OODA)** loop.  
3. **Observe:** Read the current state from the Event Log.  
4. **Orient:** Check the current step in the AOL file.  
5. **Decide:** Route the payload to the correct Extension (Tool).  
6. **Act:** Execute the tool and capture the output.

### 3.2. The "Token Snowball" Solution: Event-Sourced State

Standard agents fail due to the "Token Snowball" effect, where history grows until the context window overflows or the model becomes confused. The Executor solves this via **Event Sourcing**.

* **The Event Log:** The Executor maintains an append-only log of every action and observation. This is the **Single Source of Truth**.  
* **Stateless Execution:** The Executor components are stateless. If the system crashes, it can restart, read the Event Log to find the last successful step, and resume execution without data loss.

### 3.3. The "Translation Layer": Agent-Computer Interface (ACI)

The Executor never touches raw APIs or binaries directly. It interacts through an abstraction layer called the **Translation Layer** or **Agent-Computer Interface (ACI)**.

* **The Problem:** LLMs struggle with complex CLI flags and verbose output.  
* **The Solution:** The Executor treats every tool as a "Black Box" via the **Model Context Protocol (MCP)**.  
* *Input:* The Executor sends a clean JSON object (e.g., {"action": "convert", "file": "video.mp4"}).  
* *Translation:* A Python wrapper inside the tool translates this into the messy binary command (e.g., ffmpeg -i video.mp4 -c:v libx264...).  
* *Output:* The wrapper captures the messy stdout/stderr, filters it, and returns a clean "Observation" to the Executor.

### 3.4. Safety via Isolation (Sandboxing)

To prevent "Shared Fate" failures (where a tool crash kills the agent), the Executor implements **Optional Isolation**.

* **Containerization:** Tools (like ffmpeg or code interpreters) run inside isolated Docker containers.  
* **Entitlements:** The Executor strictly controls file system access, granting tools read/write permissions only to specific assets/ folders, preventing the agent from wiping the host system.

## 4. The Autonomous Operator Language (AOL)

AOL serves as the contract between the Planner (Reasoning) and the Executor (Action). It is designed to be human-readable for auditability but structured enough for machine parsing.

### AOL Schema Definition

The format is divided into three mandatory sections to ensure the Executor can parse dependencies before runtime.

#### Section 1: Provider Description

**Function:** Identity & Access Management.This section tells the Executor *who* it is for this session. It lists the active sessions and credentials required.

* *Example:* "Load Google Gemini Profile (RW)" or "Load Local FFmpeg Binary".  
* *Executor Action:* The Executor initializes the **Provider** component to securely unlock these credentials from the Secret Registry.

#### Section 2: User Inputs

**Function:** State Zero.This defines the initial state of the Event Log.

* **Prompt:** The raw natural language request.  
* **Resources:** File paths to initial assets (PDFs, images, raw data).

#### Section 3: Workflow Logic

**Function:** The Execution Script.This contains the sequential steps and control flow logic.

* **Step Definition:** Mapped to MCP Tool definitions (e.g., Step 1: Use ComfyUI Extension).  
* **Conditionals:** Logic gates based on Validator outputs (e.g., IF validation_score < 0.8 THEN retry).  
* **Routing:** Explicit instruction on which Extension handles which task.

## 5. Resilience & Self-Healing

The combination of AOL and the Executor allows for Level 3 Autonomy (Conditional Autonomy).

* **Validator (The Critic):** After an Extension executes, the Executor calls a Validator. This component checks the output against success criteria (e.g., "Is the video file > 0 bytes?", "Does the image contain a cat?").  
* **Self-Healing Loop:** If a step fails, the Executor does not crash. It pauses and triggers a "Feedback Loop." The Planner (LLM) is re-engaged to read the Event Log, analyze the error, and generate a *new*, corrected AOL file (e.g., changing parameters or trying a different tool).

