Set WshShell = CreateObject("WScript.Shell")
strAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
strPythonW = strAppData & "\Programs\Python\Python312\pythonw.exe"
strScript = "c:\Users\msson\OneDrive\Desktop\new LLM\maintqa_web.py"

' 1. Start Ollama if needed
WshShell.Run "powershell -Command ""if (-not (Get-Process -Name '*ollama*' -ErrorAction SilentlyContinue)) { Start-Process -FilePath '" & strAppData & "\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden }""", 0, True

' 2. Start Python server in background
WshShell.Run """" & strPythonW & """ """ & strScript & """", 0, False

' 3. Wait 3 seconds and open browser
WScript.Sleep 3500
WshShell.Run "http://localhost:8080"
