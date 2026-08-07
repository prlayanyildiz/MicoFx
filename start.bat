@echo off
REM MicoFX - sessiz baslatma.
REM Bu pencere aninda kapanir; bekleme ve tarayici acma isini start_silent.vbs yapar.
REM Konsol gormek istiyorsaniz start_console.bat kullanin (hata ayiklama girisi).
cd /d "%~dp0"
REM wscript.exe bir GUI uygulamasidir: yeni bir konsol penceresi acmaz.
start "" wscript.exe //B //Nologo "%~dp0start_silent.vbs"
exit
