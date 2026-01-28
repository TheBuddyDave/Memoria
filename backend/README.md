
# Memoria Backend

> Things that can break the code have comments with "Warning⚠️"

## Setup
Poetry handles virtualenvironments and dependencies. If you want to use it, install at: https://python-poetry.org/docs/
Alternatively, you can use pip and virtualenv.

1. Create a virtual environment:
   
   - with virtualenv: `python -m venv venv`
   
   - with poetry this command creates and activates the environment: `poetry env activate` 
   > Before activating the poetry environment, I recommend `poetry config virtualenvs.in-project true` to create the venv inside the project folder. This helps in setting the python interpreter in your IDE.
   
   > To know the path of your poetry interpreter: run `poetry env info --executable`. On VS Code you can press `Ctrl+Shift+P` or `Cmd+Shift+P` and select `Python: Select Interpreter` to set it.   

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
   - poetry: `poetry env activate`

3. Install dependencies:
   - Using pip: `pip install -r requirements.txt`
   - Using poetry: `poetry install`

#### Additional Poetry commands:
- To add a new dependency: `poetry add <package-name>`
- To remove a dependency: `poetry remove <package-name>`
- To show installed dependencies: `poetry show`
- To write to requirements.txt: `poetry export -f requirements.txt --without-hashes -o requirements.txt`. However, this requires the plugin so you have to run this once before: `poetry self add poetry-plugin-export`

## Running

Run the uvicorn server after cd to backend directory:
```bash
python main.py
```

The API will be available at http://localhost:8000 or docs at http://localhost:8000/docs

