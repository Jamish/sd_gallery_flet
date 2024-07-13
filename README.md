### Installation
`pip install -r requirements.txt`

### Running
python main.py

### Debugging
Create `.vscode/launch.json`:
```
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Flet",
            "type": "debugpy",
            "request": "launch",
            "program": "./sd_gallery_flet/main.py",
            "console": "integratedTerminal"
        }
    ]
}
```