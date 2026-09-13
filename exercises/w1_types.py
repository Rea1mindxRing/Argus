import os

def list_dir(path: str) -> list[str]:
    return os.listdir(path)  
print(list_dir("."))