Set WshShell = CreateObject("WScript.Shell")
Set oShortcut = WshShell.CreateShortcut("C:\Users\giljo\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\GiljoAI MCP\GiljoAI MCP Orchestrator.lnk")
oShortcut.TargetPath = "--help\start_giljo.bat"
oShortcut.WorkingDirectory = "--help"
oShortcut.Description = "Start the orchestrator"
oShortcut.IconLocation = "--help\frontend\public\favicon.ico"
oShortcut.Save
