## Level 1 - Using the tool

Users can use tools that work with generative to perform specific tasks. For example:

* Using Chat LLM to find information and generate a report  
* Using Google AI Studio with Nanobanana to generate a poster for a birthday party  
* Using Veo 3.1 or Kling 2.6 to generate a very short video for 8-15 seconds.

## Level 2 - Using workflow

User using tools with built-in workflow features: ComfyUI, N8N to complex tasks. This level still requires users to input, interact and feedback back and forth to get the results. Final result is granular, not complete or production-ready. It is more like a shortcut to users process. For examples:

* User using N8N workflow to categorize and filter email with the help of LLM models  
* User using ComfyUI workflow to restore old black and white photos and bring it back to life

## Level 3 - Autonomous Operator

Users use the operator and custom workflow for solving big and complex tasks with minimum human interaction. Users give requests and resources, and describe the expected output. Operator understand users request and performs reasoning to make a plan for execution. Plan is a descriptive text in which operator expects to follow and finish the task, so we can also call a plan here a workflow, with the format is more like Autonomous Operator Language, rather than JSON format or Programming coding language. Following the same plan would reproduce similar variants of a request. For example:

* A User gives prompt "create an illustration book with many colour pages for the story Goldilocks and Three Bears", the operator builds a plan, make multiple request to ComfyUI to run a predefined working workflow, keeps running in the background for 2 hours, and finally generates 23 pages of an Illustration book  
* A user gives a prompt "generate a video of a vlogger reviewing Google Pixel 13, she talks about the phone following the given script. Here is the script...", The operator took the input of a character photo, generates multi videos by request ComfyUI to run a predefined working workflow to run against prepared input, each video covers a sentence in the script for about 3 seconds. The operator takes the last frame of each video as the input for the next iteration for generating the video of the next sentence. The operator keeps generating a video for each line in the script until they finish the script. At last the operator verifies that the end video meets the condition of completion, so it stops generating and merges all the videos using ffmpeg into 1 big videos which is about 5 minutes long. The entire workflow runs in about 10 hours.

## Why level 3 autonomy?

Most of the generative AI model and tools right now as off Jan 16th, 2026 only offers the limited ability to generate small and short-form content like a single photo, a 3-8 second video, a short essay. When it comes to a complete solution that offers a long-form content like an illustrated book, 5 minutes video, or a length novel book, all of the tool get into trouble of generating content while maintaining relevant content, character identity, logical content, etc.  
We need a solution that . The solution also needs to have the ability to verify the output at each step to keep the next iteration relevant and coherent. The autonomous operator should have requirements bellow:

1. Can do planning and reasoning. Perform the plan steps by step, including making calls to available 3rd tools and ai agents to perform certain tasks.  
2. The plan (workflow of the autonomous operator) should use a certain format that ensures it reproduces the same or similar results every time. The format must be defined in a high-level language rather coding language like JSON, Node.js or Java. The workflow itself is descriptive and human-readable, easy to interact, modify, correct and share.  
3. The Autonomous Operator should have following important components: 
  * Provider: store pre-authorized credentials in the system. Provider manages the authentication for the extensions.  
  * Extension: which is an abstract layer to 3rd services and tools, For example: Extension for Google Gemini that processes prompt; Extention for ComfyUI, which interacts with the ComfyUI URL/API endpoint to request execution of a ComfyUI Workflow. etc. Extensiom simplify and delegates the duty of making 3rd tools to work with the Operator onto the 3rd tools author. Here it comes to the Agentic era. Extension must completely compatible with MCP and AI Agents. However, not all extensions are MCP or AI Agents, extension could be just a Bash shell extension, for example, which run command lines in Bash. 
  * Validator, as an optional part of the extension. Which help to verify the Extension output up to a definition of success/failure  
  * Workflow planner and executor: planner generates plans in high-level workflow language. Executor follows instruction of the workflow to call extension, wait for processing, and retrieve the output. Executor also need to call Validator to verify the output to decide what to do next. Both Planer and Executor must share the same workflow language.  
4. The workflow has 3 main sections:  
  * Section 1: Description of using the provider  
  * Section 2: User's inputs:  
    * Prompt that describes the request and what is the expected result  
    * Initial resource or reference: could be an idea, an essay, a photo, etc.  
  * Section 3: workflow logic. It describes what to do with input and output. Workflow also support condition switch to make a designed decision on certain condition.  
  * Workflow is a text file that can be shared between users. Workflow is reproducible.

