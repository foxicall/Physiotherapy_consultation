import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
 testDir: './tests/browser', timeout: 30000, fullyParallel: false,
 use: { baseURL: 'http://127.0.0.1:8765', launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {} },
 projects: [{name:'mobile',use:{...devices['Pixel 7']}},{name:'desktop',use:{viewport:{width:1440,height:1000}}}],
 webServer: {command:`${process.env.PYTHON_BIN||'python'} -m uvicorn server:api --host 127.0.0.1 --port 8765 --no-access-log`,url:'http://127.0.0.1:8765/api/health',reuseExistingServer:false,timeout:20000},
});
