Set objShell = CreateObject("Shell.Application")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this VBS script is located
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
strPythonScript = objFSO.BuildPath(strScriptPath, "control_panel.py")

' Find Python executable in venv or system
strVenvPython = objFSO.BuildPath(objFSO.GetParentFolderName(strScriptPath), "venv\Scripts\python.exe")
If objFSO.FileExists(strVenvPython) Then
    strPython = strVenvPython
Else
    strPython = "python"
End If

' Build command for Windows Terminal
strCmd = "wt.exe -w 0 nt --title ""GiljoAI Control Panel"" """ & strPython & """ """ & strPythonScript & """"

' Run as administrator
objShell.ShellExecute "wt.exe", "-w 0 nt --title ""GiljoAI Control Panel"" """ & strPython & """ """ & strPythonScript & """", "", "runas", 1
