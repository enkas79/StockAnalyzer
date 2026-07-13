; NSIS installer script for StockAnalyzer.
; Built by CI against the PyInstaller onefile output at dist\StockAnalyzer.exe.
; Version comes from the command line: makensis /DVERSION=1.2.3 installer.nsi

!ifndef VERSION
  !define VERSION "0.0.0"
!endif

Name "StockAnalyzer"
; NSIS resolves this relative to makensis's invocation directory (CI runs
; it from the repo root), not the script's own directory - keep it in sync
; with the path the workflow's upload-artifact step expects.
OutFile "packaging\windows\StockAnalyzer-Setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES64\StockAnalyzer"
RequestExecutionLevel admin

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
    SetOutPath "$INSTDIR"
    File "..\..\dist\StockAnalyzer.exe"
    CreateDirectory "$SMPROGRAMS\StockAnalyzer"
    CreateShortcut "$SMPROGRAMS\StockAnalyzer\StockAnalyzer.lnk" "$INSTDIR\StockAnalyzer.exe"
    CreateShortcut "$DESKTOP\StockAnalyzer.lnk" "$INSTDIR\StockAnalyzer.exe"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\StockAnalyzer.exe"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"
    Delete "$SMPROGRAMS\StockAnalyzer\StockAnalyzer.lnk"
    RMDir "$SMPROGRAMS\StockAnalyzer"
    Delete "$DESKTOP\StockAnalyzer.lnk"
SectionEnd
