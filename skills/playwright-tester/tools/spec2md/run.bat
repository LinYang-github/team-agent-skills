@echo off
chcp 65001 >nul
echo ========================================
echo     spec2md Playwright Spec 转换工具
echo ========================================
echo.
echo 使用方式：
echo   spec2md.exe --help          查看帮助
echo   spec2md.exe [文件]          转换 spec 文件
echo.
echo 提示：在文件浏览器中右键 .spec.ts 文件
echo       可快速转换
echo.
echo ========================================
echo.
spec2md.exe --help
echo.
echo 按任意键退出...
pause >nul
