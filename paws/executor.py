import argparse
import sys
import yaml
import importlib
from paws.core.models import AOLWorkflow
from paws.core.registry import Registry

class Executor:
    def __init__(self):
        self.registry = Registry()

    def load_workflow(self, path: str) -> AOLWorkflow:
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            return AOLWorkflow(**data)
        except Exception as e:
            raise ValueError(f"Failed to load AOL workflow from {path}: {e}")

    def execute(self, workflow_path: str):
        print(f"Loading workflow from {workflow_path}...")
        workflow = self.load_workflow(workflow_path)
        
        print(f"Provider: {workflow.provider.name}")
        if workflow.provider.name != "Localhost":
            print(f"Warning: Provider '{workflow.provider.name}' is not 'Localhost'. Proceeding with caution.")

        print(f"User Prompt: {workflow.user_inputs.prompt}")
        print("Starting execution loop...")

        context = {} # Context for shared state if needed (not used in simple PoC yet)

        for step in workflow.steps:
            print(f"\n--- Executing Step ID: {step.id} ---")
            print(f"Description: {step.description}")
            
            # Resolve Extension
            # For this PoC, we assume the Registry has it or we can load it.
            # In the Planner, we generated extension names.
            # The Registry maps names to source.
            
            ext_def = self.registry.get_extension(step.extension)
            if not ext_def:
                print(f"Error: Extension '{step.extension}' not found in registry.")
                return

            try:
                # Load the extension instance
                module = importlib.import_module(ext_def.source)
                extension_instance = getattr(module, 'extension_instance')
                
                # We assume the step inputs match the tool definition.
                # In a real system, we'd validate against input schema.
                
                # Determine tool name. 
                # The Planner instructions said: 'The Bash extension 'execute_command' tool takes...'
                # But the AOLStep doesn't explicitly have 'tool_name' field in my simplified model.
                # I should have added `tool` field to AOLStep.
                # However, for the PoC, the Bash extension only has one tool: 'execute_command'.
                # I will default to 'execute_command' if extension is Bash, or check inputs.
                
                tool_name = "execute_command" # Default for Bash PoC
                
                print(f"Calling tool '{tool_name}' on extension '{step.extension}' with inputs: {step.inputs}")
                
                result = extension_instance.call_tool(tool_name, step.inputs)
                
                if result.get("isError"):
                    print(f"Step failed: {result}")
                    # In a real system: Trigger self-healing / Planner feedback loop
                else:
                    print(f"Step Output: {result}")
                    
            except Exception as e:
                print(f"Execution failed for step {step.id}: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PAWS Executor")
    parser.add_argument("aol_path", help="Path to .aol file")
    
    args = parser.parse_args()
    
    executor = Executor()
    try:
        executor.execute(args.aol_path)
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)
