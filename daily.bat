@echo off

SET Y=%DATE:~2,2%
SET M=%DATE:~5,2%
SET D=%DATE:~8,2%
SET HH=%TIME:~0,2%
SET MM=%TIME:~3,2%
SET SS=%TIME:~6,2%
ECHO Now: %Y%/%M%/%D% %HH%:%mm%:%SS%

python .\us-daily-v2.py
python .\daily-tw-edit.py
python .\calc-tw-v3.py