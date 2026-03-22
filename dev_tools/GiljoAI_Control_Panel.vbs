Set objShell = CreateObject("Shell.Application")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this VBS script is located
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
strPythonScript = objFSO.BuildPath(strScriptPath, "control_panel.py")
strProjectRoot = objFSO.GetParentFolderName(strScriptPath)

' Find Python executable: prefer venv_devtools, then project venv, then system
strDevtoolsPython = objFSO.BuildPath(strScriptPath, "venv_devtools\Scripts\python.exe")
strVenvPython = objFSO.BuildPath(strProjectRoot, "venv\Scripts\python.exe")

If objFSO.FileExists(strDevtoolsPython) Then
    strPython = strDevtoolsPython
ElseIf objFSO.FileExists(strVenvPython) Then
    strPython = strVenvPython
Else
    strPython = "python"
End If

' Run as administrator in Windows Terminal
objShell.ShellExecute "wt.exe", "-w 0 nt --title ""GiljoAI Control Panel"" """ & strPython & """ """ & strPythonScript & """", strProjectRoot, "runas", 1
