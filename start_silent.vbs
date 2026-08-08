' MicoFX - arka planda baslat (hicbir konsol penceresi acilmaz)
'
' Onemli: eski surum, .venv\Scripts\pythonw.exe bulunamadiginda uygulamayi
' "cmd /c start /min python run.py" ile baslatiyordu. Bu satir, uygulama
' kapanana kadar gorev cubugunda duran (kucultulmus ama acik) gercek bir konsol
' penceresi birakir. Bu depoda .venv yok, yani her calistirmada o dala dusuluyordu.
' Artik her durumda WScript.Shell.Run pencere stili 0 (gizli) ile cagriliyor ve
' once konsolsuz pythonw.exe aranıyor.
Option Explicit

Dim fso, shell, env, root, exe, port, url, isRestart

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root

' restart.bat "restart" argumaniyla cagirir: kullanicinin zaten acik olan
' sekmesi var, yeni bir tane daha acmayalim. VBScript'te "And" kisa devre
' yapmaz - Count=0 iken tek satirda Arguments(0)'a bakmak "Subscript out of
' range" ile scripti tamamen durdurur, o yuzden ayri bir If ile korunuyor.
isRestart = False
If WScript.Arguments.Count > 0 Then
  isRestart = (LCase(WScript.Arguments(0)) = "restart")
End If

' Tarayiciyi bu script aciyor; run.py ikinci bir sekme acmasin.
Set env = shell.Environment("Process")
env("MICO_OPEN_BROWSER") = "0"

exe = FindPythonw(fso, shell, root)

' Pencere stili 0 = gizli, bWaitOnReturn = False = beklemeden don.
' pythonw.exe zaten konsolsuzdur; python.exe'ye dusuldugunde de 0 stili
' konsol penceresini gostermez.
'
' Dogrudan CreateProcess (WScript.Shell.Run bunu kullanir) bazen bu exe'nin
' arkasindaki Microsoft Store Python takma adini cozemiyor ve sessizce hic
' baslamiyor - PowerShell'in kendi cagirma yolu bunu guvenilir sekilde
' cozuyor, o yuzden dogrudan degil PowerShell uzerinden baslatiliyor.
shell.Run "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command ""& '" & exe & "' run.py""", 0, False

port = env("MICO_PORT")
If port = "" Then port = "8900"
url = "http://127.0.0.1:" & port

If Not isRestart Then
  WScript.Sleep 2500
  shell.Run url, 1, False
End If

Function FindPythonw(fso, shell, root)
  Dim candidates, path, i
  ' KURULUM.bat ile ayni yer: proje klasorunun disinda, sabit, senkron
  ' araclarinin (OneDrive vs.) hicbir zaman dokunamayacagi bir konum.
  candidates = Array( _
    "C:\MicoFX-venv\Scripts\pythonw.exe", _
    "C:\MicoFX-venv\Scripts\python.exe", _
    root & "\.venv\Scripts\pythonw.exe", _
    root & "\venv\Scripts\pythonw.exe", _
    root & "\.venv\Scripts\python.exe", _
    root & "\venv\Scripts\python.exe")

  For i = 0 To UBound(candidates)
    If fso.FileExists(candidates(i)) Then
      FindPythonw = candidates(i)
      Exit Function
    End If
  Next

  ' Sanal ortam yok: PATH uzerindeki konsolsuz yorumlayici.
  path = WhereExe(shell, "pythonw.exe")
  If path = "" Then path = WhereExe(shell, "python.exe")
  If path = "" Then path = "pythonw.exe"
  FindPythonw = path
End Function

' PATH'te bir exe arar. "where" ciktisi gecici dosyaya yazilir ve komut gizli
' calistigi icin ekranda hicbir sey belirmez.
Function WhereExe(shell, name)
  Dim fso2, tmp, file, line
  Set fso2 = CreateObject("Scripting.FileSystemObject")
  tmp = fso2.GetSpecialFolder(2) & "\micofx_where.txt"
  line = ""
  On Error Resume Next
  shell.Run "cmd /c where " & name & " > """ & tmp & """ 2>nul", 0, True
  If fso2.FileExists(tmp) Then
    Set file = fso2.OpenTextFile(tmp, 1)
    If Not file.AtEndOfStream Then line = Trim(file.ReadLine)
    file.Close
    fso2.DeleteFile tmp, True
  End If
  On Error GoTo 0
  If line <> "" And fso2.FileExists(line) Then
    WhereExe = line
  Else
    WhereExe = ""
  End If
End Function
