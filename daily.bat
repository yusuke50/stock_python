@echo off

SET Y=%DATE:~2,2%
SET M=%DATE:~5,2%
SET D=%DATE:~8,2%
SET HH=%TIME:~0,2%
SET MM=%TIME:~3,2%
SET SS=%TIME:~6,2%
ECHO Now: %Y%/%M%/%D% %HH%:%MM%:%SS%

IF "%~1"=="" (
  ECHO Usage: daily.bat [US|TW|ALL]
  EXIT /B 1
)

IF /I "%~1"=="US" (
  ECHO Daily US
  python .\us-daily.py || (ECHO Error running us-daily.py & EXIT /B 1)
) ELSE IF /I "%~1"=="TW" (
  ECHO Daily TW
  python .\daily-tw-edit.py || (ECHO Error running daily-tw-edit.py & EXIT /B 1)
  python .\calc-tw.py || (ECHO Error running calc-tw.py & EXIT /B 1)
) ELSE IF /I "%~1"=="ALL" (
  python .\us-daily.py || (ECHO Error running us-daily.py & EXIT /B 1)
  python .\daily-tw-edit.py || (ECHO Error running daily-tw-edit.py & EXIT /B 1)
  python .\calc-tw.py || (ECHO Error running calc-tw.py & EXIT /B 1)
) ELSE (
  ECHO Invalid task: %1
  EXIT /B 1
)