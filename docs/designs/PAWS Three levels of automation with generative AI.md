# PAWS: Three Levels of Automation with Generative AI

## Level 1: Using the Tool

At this level, users interact directly with generative AI tools to perform specific, isolated tasks.

**Examples:**
* Using a Chat LLM to research information and generate a report.
* Using Google AI Studio with Nanobanana to generate a poster for a birthday party.
* Using Veo 3.1 or Kling 2.6 to generate a very short video (8-15 seconds).

## Level 2: Using Workflows

Users leverage tools with built-in workflow features, such as ComfyUI or n8n, to handle more complex tasks. This level still requires significant user input, interaction, and iterative feedback to achieve the desired outcome. The final results are often granular components rather than a complete, production-ready product. Workflows at this level act as process accelerators for the user.

**Examples:**
* A user utilizing an n8n workflow to categorize and filter emails with the assistance of LLM models.
* A user utilizing a ComfyUI workflow to restore and colorize old black-and-white photos.

## Level 3: Autonomous Operator

Users employ an autonomous operator and custom workflows to solve large, complex tasks with minimal human interaction. Users provide the initial request, necessary resources, and a description of the expected output. The operator understands the request and performs reasoning to create an execution plan.

This plan is a descriptive text that the operator follows to complete the task. We refer to this plan as a workflow, written in an Autonomous Operator Language (AOL) rather than a rigid JSON format or a low-level programming language. Following the same plan allows for reproducible results or similar variants of a request.

**Examples:**
* **Illustration Book:** A user provides the prompt: "Create an illustration book with many colored pages for the story 'Goldilocks and the Three Bears'." The operator builds a plan, makes multiple requests to ComfyUI to run a predefined workflow, keeps running in the background for 2 hours, and finally generates a 23-page illustration book.
* **Long-form Video:** A user provides the prompt: "Generate a video of a vlogger reviewing the Google Pixel 13. She talks about the phone following the given script. Here is the script..." The operator takes a photo of the character as input and generates multiple video segments by requesting ComfyUI to run a predefined workflow against prepared inputs. Each video segment covers a sentence in the script (approx. 3 seconds). The operator uses the last frame of each segment as the input for the next iteration to ensure visual continuity. This process repeats until the entire script is covered. Finally, the operator verifies that the content meets the completion conditions and merges all segments using FFmpeg into a single 5-minute video. The entire workflow takes about 10 hours to complete.

## Why Level 3 Autonomy?

As of January 16th, 2026, most generative AI models and tools offer limited ability to generate only small, short-form content (e.g., a single photo, a 3-8 second video, or a short essay). When attempting to create complete solutions producing long-form content—such as an illustrated book, a 5-minute video, or a full-length novel—these tools struggle to maintain context, character identity, and logical coherence over time.

We need a solution that bridges this gap. This solution must be able to verify the output at each step to keep the next iteration relevant and coherent. An Autonomous Operator should meet the following requirements:

1.  **Planning and Reasoning:** It must be able to plan and reason, performing steps sequentially. This includes making calls to third-party tools and AI agents to execute specific tasks.
2.  **Reproducible Workflows:** The plan (the operator's workflow) should use a format that ensures reproducible results. This format must be defined in a high-level language rather than a coding language like JSON, Node.js, or Java. The workflow itself should be descriptive, human-readable, and easy to interact with, modify, correct, and share.
3.  **Core Components:** The Autonomous Operator consists of the following key components:
    *   **Provider:** Stores pre-authorized credentials within the system and manages authentication for extensions.
    *   **Extension:** An abstraction layer for third-party services and tools. For example, an extension for Google Gemini processes prompts, while an extension for ComfyUI interacts with its API to execute workflows. Extensions simplify the integration of third-party tools, delegating compatibility to the tool's author. While extensions should ideally be compatible with MCP (Model Context Protocol) and AI Agents, they can also be simple implementations, such as a Bash extension for running command-line instructions.
    *   **Validator (Optional):** A component within an extension that verifies the output against a definition of success or failure.
    *   **Workflow Planner and Executor:** The **Planner** generates plans in the high-level workflow language. The **Executor** follows the workflow instructions to call extensions, wait for processing, and retrieve output. The Executor also invokes Validators to verify output and decide the next steps. Both Planner and Executor must utilize the same workflow language.
4.  **Workflow Structure:** The workflow consists of three main sections:
    *   **Section 1: Provider Description:** Describes the providers being used.
    *   **Section 2: User Inputs:**
        *   Prompts describing the request and expected result.
        *   Initial resources or references (e.g., an idea, an essay, a photo).
    *   **Section 3: Workflow Logic:** Describes how to process inputs and outputs, including conditional switching to make design decisions based on specific criteria.
    *   **Characteristics:** The workflow is a text file that acts as a reproducible recipe, easily shared between users.

