import os
import re
import yaml
from pathlib import Path
from typing import Any, Union

from utils.logger import get_logger

logger = get_logger('yaml_loader')


def expand_env_vars(data: Any) -> Any:
    """Recursively expand environment variables in data using $VAR_NAME format.
    
    Args:
        data: The data to process (can be dict, list, str, or any other type)
        
    Returns:
        Data with environment variables expanded
        
    Raises:
        ValueError: If an environment variable is not found
    """
    if isinstance(data, str):
        # Pattern to match $VAR_NAME
        pattern = r'\$([A-Za-z_][A-Za-z0-9_]*)'
        
        def replace_env_var(match):
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' not found")
            return value
        
        return re.sub(pattern, replace_env_var, data)
    elif isinstance(data, dict):
        return {key: expand_env_vars(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    else:
        return data


def load_yaml_with_env(file_path: Union[str, Path]) -> dict:
    """Load YAML file and expand environment variables.
    
    Args:
        file_path: Path to the YAML file
        
    Returns:
        Dictionary with environment variables expanded
        
    Raises:
        FileNotFoundError: If YAML file doesn't exist
        ValueError: If environment variable is not found
        yaml.YAMLError: If YAML parsing fails
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            yaml_data = yaml.safe_load(f) or {}
        
        logger.info(f"Loaded YAML configuration from {file_path}")
        
        # Expand environment variables
        expanded_data = expand_env_vars(yaml_data)
        
        logger.debug("Environment variables expanded successfully")
        return expanded_data
        
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file {file_path}: {e}")
        raise
    except ValueError as e:
        logger.error(f"Environment variable expansion failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load YAML file {file_path}: {e}")
        raise