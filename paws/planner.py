import os
import sys
import argparse
import asyncio
import logging
from importlib.resources import files
from typing import List
from dotenv import load_dotenv
from google import genai
from google.genai import types

from paws.core.models import AOLWorkflow, AOLProvider, AOLUserInputs, AOLStep, AOLExtension
from paws.core.registry import Registry

load_dotenv()

# Configure logging from environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _load_aol_specification() -> str:
    """Load the AOL Specification from package resources."""
    return files("paws.aol_spec").joinpath("AOL Specification.md").read_text()

class Planner:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.registry = Registry()

    def _get_system_prompt(self) -> str:
        # Load AOL specification from package resources
        aol_spec = _load_aol_specification()
        
        # Discover available extensions
        extensions = self.registry.discover_extensions()
        tools_desc = []
        for ext in extensions:
            # Dynamic import to get tool definition
            # For PoC we assume the registry source path is importable
            try:
                module = __import__(ext.source, fromlist=['extension_instance'])
                tool_def = module.extension_instance.get_tool_definition()
                tools_desc.append(f"- Extension '{ext.name}': {tool_def}")
            except Exception as e:
                print(f"Warning: Could not load extension {ext.name}: {e}")

        extensions_text = chr(10).join(tools_desc) if tools_desc else "No extensions available."

        return f"""You are the PAWS Planner. You compile user requests into an Autonomous Operator Language (AOL) Workflow.

## Instructions
1. Read and understand the AOL Specification below
2. Generate a valid AOL workflow in JSON format
3. Output MUST be a valid JSON object matching the AOL schema (provider, user_inputs, steps)

## Available Extensions
{extensions_text}

## AOL Specification
{aol_spec}
"""

    def plan(self, prompt: str) -> AOLWorkflow:
        system_prompt = self._get_system_prompt()
        
        # We cannot use response_schema because Gemini API does not support free-form dicts (additionalProperties) well yet.
        # We rely on the prompt description and JSON mode.

        response = self.client.models.generate_content(
            model=os.getenv("GEMINI_MODEL_NAME", "gemini-3-pro-preview"),
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
        )
        
        try:
             if response.text:
                import json
                data = json.loads(response.text)
                logger.debug(f"Gemini response: {response.text}")
                return AOLWorkflow(**data)
             else:
                 raise ValueError("Empty response from Gemini")
        except Exception as e:
             raise ValueError(f"Failed to parse AOLWorkflow from Gemini response: {e}")

import yaml

def str_representer(dumper, data):
    """Custom representer for strings. Uses block style for multi-line or complex strings."""
    # Use literal block style (|) for strings containing newlines or special chars
    if '\n' in data or len(data) > 80 or '|' in data or ':' in data or "'" in data or '"' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

def save_aol(aol: AOLWorkflow, path: str):
    # Ensure .aol extension
    if not path.endswith(".aol"):
        path = path + ".aol"
    
    # Add custom string representer
    yaml.add_representer(str, str_representer)
    
    with open(path, 'w') as f:
        # Dump pydantic model to dict, excluding None values for cleaner output
        yaml.dump(aol.model_dump(exclude_none=True), f, sort_keys=False, indent=2, default_flow_style=False, allow_unicode=True)
    
    return path  # Return actual path in case extension was added

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PAWS Planner")
    parser.add_argument("prompt", help="The user prompt")
    parser.add_argument("output", help="Output path for .aol file")
    
    args = parser.parse_args()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        sys.exit(1)
        
    planner = Planner(api_key)
    try:
        aol = planner.plan(args.prompt)
        save_aol(aol, args.output)
        print(f"Plan saved to {args.output}")
    except Exception as e:
        print(f"Error generating plan: {e}")
        sys.exit(1)
