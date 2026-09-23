$ErrorActionPreference = "Stop"

winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
winget install -e --id EclipseAdoptium.Temurin.21.JDK --accept-package-agreements --accept-source-agreements
winget install -e --id MSYS2.MSYS2 --accept-package-agreements --accept-source-agreements

# GCC 설치
$bash = "C:\msys64\usr\bin\bash.exe"
& $bash -lc "pacman -Syu --noconfirm"
& $bash -lc "pacman -S --needed --noconfirm mingw-w64-ucrt-x86_64-gcc"

# GCC PATH 등록
$gccPath = "C:\msys64\ucrt64\bin"
$path = [Environment]::GetEnvironmentVariable("Path", "Machine")

if ($path -notlike "*$gccPath*") {
    [Environment]::SetEnvironmentVariable(
        "Path",
        "$path;$gccPath",
        "Machine"
    )
}

Write-Host "`nInstallation complete."
Write-Host "Open a NEW PowerShell and run:"
Write-Host "python --version"
Write-Host "java -version"
Write-Host "javac -version"
Write-Host "gcc --version"