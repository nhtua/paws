# Technical Design: PAWS Phase 1 (Core Execution Engine)

## 1. Executive Summary

Phase 1 focuses on building the runtime foundation for the **Progressive Autonomous Workflow Server (PAWS)**, a Level 3 Autonomous Operator. The primary objective is to decouple **reasoning** (the Planner) from **action** (the Executor). This is achieved through two core innovations:

1. **Autonomous Operator Language (AOL):** A human-readable, text-based "source of truth" for workflows. 
2. **The "Translation Layer" Extension Architecture:** A standardized method for wrapping complex tools (like ffmpeg) into abstract **Model Context Protocol (MCP)** servers.

## 2. Data Design: The Autonomous Operator Language (AOL)

To meet the requirement for a "human-readable, easy to understand and edit" format, PAWS rejects complex JSON schemas in favor of a structured, Markdown-like syntax.

### 2.1. The Self-Complete & Self-Healing Logic

The AOL file acts as the bridge between the user's intent and the system's execution.

* **Self-Complete:** The Planner (LLM) takes a vague user prompt (e.g., "Make a video") and generates a precise AOL file, filling in necessary steps and resource paths.  
* **Self-Healing:** If a workflow fails, the Planner uses the "Event Log" and the broken AOL file to regenerate a corrected version, which the Executor then resumes.

### 2.2. AOL Schema Definition

The following schema demonstrates a video generation workflow using the ffmpeg extension: 

```markdown
# PAWS Workflow Definition: Video Synthesis

# Section 1: Provider Context  
Provider: Google_Gemini_Pro_1.5  
Auth_Scope: Read_Write_Filesystem  
Credentials: vault_id_8821 [masked]

# Section 2: User Inputs  
Prompt: "Create a 5-minute video compilation from the generated clips."  
Resources:  
  - ./assets/clip_01.mp4  
  - ./assets/clip_02.mp4  
  - ./assets/intro_music.mp3

# Section 3: Workflow Logic  
The Planner writes simple instructions; the Extension handles the complexity.

STEP 1: VALIDATE resources exist using System.FileCheck.  
STEP 2: EXECUTE Extension.FFmpeg.Combine_Videos(  
    input_files=["./assets/clip_01.mp4", "./assets/clip_02.mp4"],  
    output_name="./final_render.mp4"  
)  
CONDITION: IF Step_2.output == "Error: Encoding Fail" THEN GOTO Step_2 (Retry with safe_mode=True).  
STEP 3: SAVE ./final_render.mp4 to User_Output_Folder.
```

## 3. Extensible Extension Architecture (The "Translation Layer")

Phase 1 implements a modular "Tool Layer" that strictly isolates the Executor from the technical details of 3rd-party tools.

### 3.1. Design Principle: The "Black Box" Abstraction

The Executor (and the human user) should effectively treat tools as "black boxes".

* **The Executor's View:** It sees a clean, high-level function call (e.g., combine_videos).  
* **The Extension's Reality:** It manages complex CLI flags, API authentication, and error handling internally.  
* **Benefit:** This prevents the "Autonomy Paradox" where the agent struggles with the verbosity of standard CLI interfaces.

### 3.2. Technical Implementation: The Wrapper Pattern

To integrate non-AI tools like ffmpeg into the PAWS Agentic Loop, we utilize the **Model Context Protocol (MCP)**. Since ffmpeg is a binary command-line tool, the Extension acts as a **Translator/Wrapper**.

#### Case Study: The FFmpeg Extension

This demonstrates how a complex binary is converted into an MCP Server for PAWS.  
**A. The Architecture**

1. **The Raw Tool:** ffmpeg binary (handles video processing).  
2. **The Extension (MCP Server):** A Python script running in a sandbox.  
3. **The Interface (ACI):** A simplified JSON definition exposed to the Executor.

**B. Implementation Logic (Python Wrapper)**The Extension code performs three distinct "Translation" steps to hide complexity:

**Step 1: Interface Definition (MCP)**Instead of exposing ffmpeg's thousands of flags, the Python wrapper exposes a simplified schema to the PAWS Executor:  
```python
# Defined in extension.py  
@mcp.tool()  
def combine_videos(file_paths: list[str], output_filename: str) -> str:  
    """Merges multiple video files into one seamless file."""  
    # The Executor sees ONLY this simple signature. 
```

**Step 2: Internal Translation (The "Logic")** When called, the Python script translates the simple request into the complex command line syntax required by the binary:  
```python
def internal_logic(file_paths, output_filename):  
    # 1. Create the temporary input list required by ffmpeg  
    with open("input_list.txt", "w") as f:  
        for path in file_paths:  
            f.write(f"file '{path}'\\n")  
   
    # 2. Construct the complex command line string  
    # The Planner does NOT need to know about '-f concat' or '-safe 0'  
    command = [  
        "ffmpeg",  
        "-f", "concat",  
        "-safe", "0",  
        "-i", "input_list.txt",  
        "-c", "copy",  # Stream copy for speed  
        output_filename  
    ]  
   
    # 3. Execute in Sandbox  
    result = subprocess.run(command, capture_output=True, text=True)  
    return result  
```
**Step 3: Standardized Output**The wrapper captures the raw stderr output from ffmpeg and converts it into a standardized PAWS response.  
  * *If Success:* Returns {"status": "success", "path": "./final\_render.mp4"}.  
  * *If Fail:* Returns a clean error message that the **Validator** can read to trigger a retry loop.

### 3.3. Isolation and Sandboxing

To ensure stability, extensions are deployed using **Optional Isolation**:

* **Containerization:** The ffmpeg extension runs inside a Docker container. If ffmpeg consumes 100% CPU or crashes, it does not kill the main PAWS Executor process.  
* **Entitlements:** The Extension is granted specific file system permissions (e.g., read access to ./assets/ only), preventing it from overwriting system files.

## 4. The Core Execution Engine

Phase 1 builds the engine that drives the Agentic Loop.

### 4.1. The Executor (Runtime Engine)

The Executor functions as a strict **MCP Client**.

* **Protocol Adherence:** It does not know how to run ffmpeg. It only knows how to send an MCP JSON-RPC message (call_tool).
* **Decoupling:** This allows the underlying tool to change (e.g., swapping ffmpeg for a cloud transcoding API) without changing the AOL workflow file or the Executor code.

### 4.2. The Validator (The Critic)

The Validator acts as the quality gate between the Extension and the next step.

* **In the FFmpeg context:** After the extension reports "Success," the Validator might perform a "Semantic Check" (using a Vision model) to ensure the output video actually plays and isn't just a corrupt file with a valid extension.

## 5. Summary of Phase 1 Deliverables

1. **AOL Parser:** A Python module to read and validate the text-based Workflow Plans.  
2. **MCP Extension SDK:** A Python template for developers to wrap tools (like ffmpeg) into MCP servers.  
3. **Event-Sourced Executor:** The main loop that reads steps, calls MCP tools, and logs events for the "Self-Healing" mechanism.

