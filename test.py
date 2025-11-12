# import os
from pathlib import Path
import modal

training_code_dir = Path(__file__).parent / "src/stt"


print(training_code_dir)