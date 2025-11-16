
import os 
from huggingface_hub import create_repo

from pathlib import Path 
from dotenv import load_dotenv 

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

hfToken = os.environ.get("HUGGINGFACE_HUB_TOKEN")
hfUserName = os.environ.get("HF_USER_NAME")

repo_id = hfUserName+"/model"
create_repo(repo_id=repo_id, private=False, token = hfToken , exist_ok=True)
print(f"Repository '{repo_id}' created successfully.")



print("*"*80)
