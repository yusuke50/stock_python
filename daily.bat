@echo off

SET Y=%DATE:~2,2%
SET M=%DATE:~5,2%
SET D=%DATE:~8,2%
SET HH=%TIME:~0,2%
SET MM=%TIME:~3,2%
SET SS=%TIME:~6,2%
ECHO Now: %Y%/%M%/%D% %HH%:%mm%:%SS%

IF /I "%~1"=="US" (
  ECHO Daily US
  python .\us-daily.py
) ELSE IF /I "%~1"=="TW" (
  ECHO Daily TW
  python .\daily-tw-edit.py
  python .\calc-tw.py
) ELSE (
  ECHO Invalid task: %1
  EXIT /B 1
)