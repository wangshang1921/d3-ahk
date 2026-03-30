# d3-ahk

Windows desktop auto-key application built with Python and PySide6.

## Features

- One global toggle hotkey (start/stop) with user-selected combination: `Shift/Ctrl/Alt` + `Letter`
- Up to 10 independently scheduled trigger slots
- Keyboard keys plus mouse left, right, wheel up, and wheel down
- Two-page UI: configuration window and top overlay runtime window
- Configurations stored under `%USERPROFILE%\\.d3ahk` as JSON

## Run

```powershell
pip install -r requirements.txt
python main.py
```

## Notes

- The runtime overlay is always pinned to the top of the screen.
- Double-click the runtime overlay to reopen the configuration window.
- For wheel actions, each interval sends one wheel step.
