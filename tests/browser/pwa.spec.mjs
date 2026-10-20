import {test,expect} from '@playwright/test';
const nav=(page,name)=>page.locator((test.info().project.name==='mobile'?'.mobile-nav':'.desktop-nav')+` [data-nav="${name}"]`);
test('search, favorite, detail, selection, prices and installation help',async({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/');await expect(page.locator('.syndrome-card')).toHaveCount(50);
 await page.locator('#search').fill('網球軸');await expect(page.locator('.syndrome-card').first()).toContainText('網球肘');
 await page.locator('.favorite-button').first().click();await page.locator('.card-title').first().click();
 await expect(page.locator('#syndrome-dialog')).toBeVisible();await expect(page.locator('.detail-field')).toHaveCount(6);
 await page.locator('#use-syndrome').click();await expect(page.locator('#syndrome-select')).toHaveValue('13');
 await page.locator('#symptom').fill('提物時手肘疼痛');await page.locator('#syndrome-select').selectOption('41');await expect(page.locator('#symptom')).toHaveValue('');
 await nav(page,'clinic').click();await expect(page.locator('#package-prices')).toContainText('20,900');await expect(page.locator('#package-prices')).toContainText('1,600');
 await page.locator('#install-secondary').click();await expect(page.locator('#install-dialog')).toBeVisible();await expect(page.locator('#install-dialog')).toContainText('Safari');
 await page.locator('[data-close="install-dialog"]').click();await nav(page,'library').click();await page.locator('#search').fill('');await page.locator('#favorites-filter').click();await expect(page.locator('.syndrome-card')).toHaveCount(1);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
test('offline reload retains all 50 records and cached shell, excluding API',async({page,context})=>{
 await page.goto('/');await expect(page.locator('.syndrome-card')).toHaveCount(50);
 await page.evaluate(async()=>{await navigator.serviceWorker.ready;if(!navigator.serviceWorker.controller)await new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true}));});
 await context.setOffline(true);await page.reload();await expect(page.locator('.syndrome-card')).toHaveCount(50);await expect(page.locator('#connection-status')).toContainText('離線模式');
 await page.locator('#search').fill('PFPS');await expect(page.locator('.syndrome-card').first()).toContainText('髕骨股骨');
 await nav(page,'workspace').click();await expect(page.locator('#generate-button')).toBeDisabled();
 const cached=await page.evaluate(async()=>{const urls=[];for(const name of await caches.keys())for(const request of await (await caches.open(name)).keys())urls.push(request.url);return urls;});
 expect(cached.length).toBeGreaterThan(8);expect(cached.some(url=>url.includes('/api/'))).toBe(false);
});
test('real UI request path renders only returned model text and surfaces errors',async({page})=>{
 await page.route('**/api/health',route=>route.fulfill({json:{status:'ok',generation_enabled:true}}));
 await page.route('**/api/session',route=>route.fulfill({json:{token:'test-session',expires_in:3600}}));
 let requestBody;
 await page.route('**/api/generate',route=>{requestBody=route.request().postDataJSON();return route.fulfill({json:{guide:'## 1. 同理\n**您好**\n<script>alert(1)</script>',syndrome:'足底筋膜炎',syndrome_id:41}});});
 await page.goto('/#workspace');await page.locator('#syndrome-select').selectOption('41');await page.locator('#access-code').fill('test-code');await page.locator('#login-button').click();
 await expect(page.locator('#generate-button')).toBeEnabled();await page.locator('#symptom').fill('早上下床腳跟痛');await page.locator('#generate-button').click();
 await expect(page.locator('#result-content')).toContainText('您好');await expect(page.locator('#result-content script')).toHaveCount(0);expect(requestBody.syndrome_id).toBe(41);expect(requestBody.symptom).toBe('早上下床腳跟痛');
 await page.unroute('**/api/generate');await page.route('**/api/generate',route=>route.fulfill({status:429,json:{detail:'請稍候一分鐘再試。'}}));await page.locator('#generate-button').click();await expect(page.locator('#generation-error')).toContainText('請稍候');await expect(page.locator('#result-content')).toContainText('您好');
 expect(await page.evaluate(()=>localStorage.getItem('clinic-access-code'))).toBe(null);
});
