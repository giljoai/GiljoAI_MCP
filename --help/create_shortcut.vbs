Set WshShell = CreateObject("WScript.Shell")
Set oShortcut = WshShell.CreateShortcut("C:\Users\giljo\Desktop\GiljoAI MCP Orchestrator.lnk")
oShortcut.TargetPath = "--help\start_giljo.bat"
oShortcut.WorkingDirectory = "--help"
oShortcut.Description = "AI-Powered Development Orchestration System"
oShortcut.IconLocation = "--help\frontend\public\favicon.ico"
oShortcut.Save
