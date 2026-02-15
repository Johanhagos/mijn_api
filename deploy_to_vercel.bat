@echo off
echo ========================================
echo   VERCEL DEPLOYMENT SCRIPT
echo   Webshop Frontend Deployment
echo ========================================
echo.

cd webshop_for_upload

echo [1/3] Checking Vercel CLI...
vercel --version
if %errorlevel% neq 0 (
    echo ERROR: Vercel CLI not found!
    echo Run: npm install -g vercel
    pause
    exit /b 1
)

echo.
echo [2/3] Deploying to Vercel Production...
echo This will deploy your modern webshop frontend.
echo.

vercel --prod

echo.
echo [3/3] Deployment Complete!
echo.
echo Next steps:
echo 1. Open the Vercel URL in incognito mode
echo 2. Test the green gradient homepage
echo 3. Click the AI chat button (bottom right)
echo 4. Try the checkout page
echo.
echo To add custom domain:
echo 1. Go to https://vercel.com/dashboard
echo 2. Select your project
echo 3. Settings -^> Domains -^> Add apiblockchain.io
echo.
pause
