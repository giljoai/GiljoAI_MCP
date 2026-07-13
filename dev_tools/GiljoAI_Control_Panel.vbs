Set objShell = CreateObject("Shell.Application")
Set objFSO = CreateObject("Scripting.FileSystemObject")
Set wshShell = CreateObject("WScript.Shell")

' Get the directory where this VBS script is located
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
strProjectRoot = objFSO.GetParentFolderName(strScriptPath)

' Validate venv integrity: check pyvenv.cfg (not just python.exe)
strDevtoolsPython = objFSO.BuildPath(strScriptPath, "venv_devtools\Scripts\python.exe")
strDevtoolsCfg = objFSO.BuildPath(strScriptPath, "venv_devtools\pyvenv.cfg")

If objFSO.FileExists(strDevtoolsPython) And objFSO.FileExists(strDevtoolsCfg) Then
    ' Isolated venv is healthy -- launch directly
    strPython = strDevtoolsPython
    strPythonScript = objFSO.BuildPath(strScriptPath, "control_panel.py")
    objShell.ShellExecute "wt.exe", "-w 0 nt --title ""GiljoAI Control Panel"" """ & strPython & """ """ & strPythonScript & """", strProjectRoot, "runas", 1
Else
    ' venv_devtools missing or corrupted -- delegate to batch launcher which auto-bootstraps
    strBatLauncher = objFSO.BuildPath(strScriptPath, "launch_control_panel.bat")
    objShell.ShellExecute "wt.exe", "-w 0 nt --title ""GiljoAI Control Panel"" cmd /c """ & strBatLauncher & """", strProjectRoot, "runas", 1
End If
