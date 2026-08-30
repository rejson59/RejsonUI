' Uruchamia Amber w tle (bez okna konsoli) przy starcie systemu.
' Uzyj install_autostart.bat, aby zarejestrowac ten skrypt w autostarcie.
Set shell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = scriptDir
shell.Run "cmd /c start_amber.bat", 0, False
