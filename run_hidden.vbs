Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = scriptDir & "\.venv\Scripts\python.exe"
mainPy = scriptDir & "\src\main.py"
cmd = Chr(34) & pythonExe & Chr(34) & " " & Chr(34) & mainPy & Chr(34)
WshShell.CurrentDirectory = scriptDir
WshShell.Run cmd, 0, False
