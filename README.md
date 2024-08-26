### Installation
`pip install -r requirements.txt`

### Running
python main.py

### Re-generating main.spec
`pip install pyinstaller`
`pyinstaller --onefile main.py`

### Compiling for Windows
`rm -rf build/ && rm -rf dist/ && pyinstaller main.spec`