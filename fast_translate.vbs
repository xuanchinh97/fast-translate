Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir
pythonExe = strDir & "\.venv\Scripts\python.exe"
mainPy = strDir & "\src\main.py"
WshShell.Run """" & pythonExe & """ """ & mainPy & """", 0, False
