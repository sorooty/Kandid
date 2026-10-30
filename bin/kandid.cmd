@echo off
rem Windows twin of bin/kandid: PowerShell and cmd cannot run the bash script and would open
rem the "Open with" dialog instead. Runs the Kandid CLI from the plugin's own Python project.
uv run --quiet --frozen --no-dev --project "%~dp0.." kandid %*
