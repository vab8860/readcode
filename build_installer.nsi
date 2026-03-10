!include "MUI2.nsh"
!include "LogicLib.nsh"

Name "ReadCode"
OutFile "ReadCodeInstaller.exe"
InstallDir "$PROGRAMFILES\ReadCode"
InstallDirRegKey HKCU "Software\ReadCode" "InstallDir"
RequestExecutionLevel admin

!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  WriteRegStr HKCU "Software\ReadCode" "InstallDir" "$INSTDIR"

  File "dist\readcode.exe"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Add to PATH for all users
  ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  StrCpy $1 $0
  ; Append only if not already present
  Push $1
  Push "$INSTDIR"
  Call StrContains
  Pop $2
  ${If} $2 == 0
    StrCpy $1 "$1;$INSTDIR"
    WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$1"
    System::Call 'user32::SendMessageTimeoutW(i 0xffff,i ${WM_SETTINGCHANGE},i 0,t "Environment",i 0x0002,i 5000,*i .r2)'
  ${EndIf}

SectionEnd

Section "Uninstall"
  ; Remove from PATH
  ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
  StrCpy $1 $0
  ; Remove occurrences of ;$INSTDIR and $INSTDIR;
  Push $1
  Push ";$INSTDIR"
  Call un.StrReplace
  Pop $1
  Push $1
  Push "$INSTDIR;"
  Call un.StrReplace
  Pop $1
  ; Remove remaining exact match
  ${If} $1 == "$INSTDIR"
    StrCpy $1 ""
  ${EndIf}
  WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" "$1"
  System::Call 'user32::SendMessageTimeoutW(i 0xffff,i ${WM_SETTINGCHANGE},i 0,t "Environment",i 0x0002,i 5000,*i .r2)'

  Delete "$INSTDIR\readcode.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "Software\ReadCode"
SectionEnd

Function un.StrReplace
  Exch $R1
  Exch
  Exch $R0
  Push $R2
  Push $R3
  Push $R4
  StrLen $R2 $R0
  StrCpy $R3 ""
loop:
  StrCpy $R4 $R1 $R2
  StrCmp $R4 $R0 found
  StrCmp $R1 "" done
  StrCpy $R3 "$R3$R4"
  StrCpy $R1 $R1 "" 1
  Goto loop
found:
  StrCpy $R1 $R1 "" $R2
  Goto loop
done:
  Pop $R4
  Pop $R3
  Pop $R2
  Pop $R0
  Exch $R3
FunctionEnd

Function StrContains
  Exch $R1 ; needle
  Exch
  Exch $R0 ; haystack
  Push $R2
  Push $R3
  StrLen $R2 $R1
  StrCpy $R3 0
loop_sc:
  StrCmp $R0 "" done_sc
  StrCpy $R4 $R0 $R2
  StrCmp $R4 $R1 found_sc
  StrCpy $R0 $R0 "" 1
  Goto loop_sc
found_sc:
  StrCpy $R3 1
done_sc:
  Pop $R3
  Pop $R2
  Pop $R0
  Exch $R3
FunctionEnd
