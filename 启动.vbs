Set ws = CreateObject("WScript.Shell")
ws.CurrentDirectory = Left(WScript.ScriptFullName, Len(WScript.ScriptFullName) - Len(WScript.ScriptName))
ws.Run "pythonw.exe src\main.py", 0, False