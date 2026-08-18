$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c "D:\Code\tw-stock\daily.bat" ALL' -WorkingDirectory 'D:\Code\tw-stock'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 19:00
Register-ScheduledTask -TaskName 'tw-stock-daily' -Action $action -Trigger $trigger -Force
