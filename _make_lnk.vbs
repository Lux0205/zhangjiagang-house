
Set ws = CreateObject("WScript.Shell")
Set sc = ws.CreateShortcut("d:\zzz\张家港房价app\张家港房价K线图.lnk")
sc.TargetPath = "D:\python\pythonw.exe"
sc.Arguments = "src\main.py"
sc.WorkingDirectory = "d:\zzz\张家港房价app"
sc.WindowStyle = 1
sc.Save
