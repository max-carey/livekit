import os
import yaml
from pathlib import Path

def load_prompt(prompt_name: str) -> str:
    """Load a prompt from a YAML file.
    
    Args:
        prompt_name: Name of the prompt file without .yaml extension
        
    Returns:
        The prompt string
    """
    prompts_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    yaml_path = prompts_dir / f"{prompt_name}.yaml"
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {yaml_path}")
        
    with open(yaml_path, 'r') as f:
        prompt_data = yaml.safe_load(f)
        
    return prompt_data['system_prompt'] 