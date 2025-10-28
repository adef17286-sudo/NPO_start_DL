@echo off
echo Downloading Bento4 for Windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $page = Invoke-WebRequest -Uri 'https://www.bento4.com/downloads/'; $link = ($page.Links | Where-Object { $_.href -like '*.zip' -and $_.outerText -like '*Binaries for Windows*' } | Select-Object -ExpandProperty href -First 1); if ($link) { $uri = New-Object System.Uri('https://www.bento4.com/downloads/'); $zipUrl = New-Object System.Uri($uri, $link); Write-Host ('Downloading from: ' + $zipUrl.AbsoluteUri); Invoke-WebRequest -Uri $zipUrl.AbsoluteUri -OutFile 'mp4decrypt.zip'; Write-Host 'Successfully downloaded to mp4decrypt.zip'; } else { Write-Host 'Could not find a suitable download link.'; exit 1; } } catch { Write-Host ('An error occurred: ' + $_.Exception.Message); exit 1; }"

echo.
echo Extracting mp4decrypt.exe...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Expand-Archive -Path 'mp4decrypt.zip' -DestinationPath '.' -Force; $extractedFolder = Get-ChildItem -Path '.' -Directory | Where-Object { $_.Name -like 'Bento4-SDK*' }; if ($extractedFolder) { $mp4decryptPath = Join-Path -Path $extractedFolder.FullName -ChildPath 'bin\mp4decrypt.exe'; if (Test-Path $mp4decryptPath) { Move-Item -Path $mp4decryptPath -Destination '.'; Write-Host 'Successfully extracted mp4decrypt.exe'; } else { Write-Host 'mp4decrypt.exe not found in the extracted folder.'; } Remove-Item -Path $extractedFolder.FullName -Recurse -Force; } else { Write-Host 'Could not find the extracted folder.'; } } catch { Write-Host ('An error occurred during extraction: ' + $_.Exception.Message); }"

echo.
echo Cleaning up...
del mp4decrypt.zip

echo.
echo Downloading N_m3u8DL-RE for Windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $releaseInfo = Invoke-RestMethod -Uri 'https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest'; $asset = $releaseInfo.assets | Where-Object { $_.name -like '*win-x64*' } | Select-Object -First 1; if ($asset) { Write-Host ('Downloading from: ' + $asset.browser_download_url); Invoke-WebRequest -Uri $asset.browser_download_url -OutFile 'N_m3u8DL-RE.zip'; Write-Host 'Successfully downloaded to N_m3u8DL-RE.zip'; } else { Write-Host 'Could not find a suitable download link for N_m3u8DL-RE.'; exit 1; } } catch { Write-Host ('An error occurred: ' + $_.Exception.Message); exit 1; }"

echo.
echo Extracting N_m3u8DL-RE...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Expand-Archive -Path 'N_m3u8DL-RE.zip' -DestinationPath '.' -Force; Write-Host 'Successfully extracted N_m3u8DL-RE'; } catch { Write-Host ('An error occurred during extraction: ' + $_.Exception.Message); }"

echo.
echo Cleaning up...
del N_m3u8DL-RE.zip

echo.
echo Done.
echo Press any key to exit.
pause > nul