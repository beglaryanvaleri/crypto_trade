from dotenv import load_dotenv
from src.utils.yaml_loader import load_yaml_with_env

load_dotenv()

class Config:
    yaml = load_yaml_with_env("config.yaml")