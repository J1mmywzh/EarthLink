// Runs against a disposable fixture server; never needs a map key.
const {chromium}=require(process.env.EARTHLINK_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.EARTHLINK_CHROME||undefined,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1280,height:800}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('earthlink:skipKeys','true'));
 await page.goto(process.argv[2]||'http://127.0.0.1:8877/');
 await page.waitForFunction(()=>window.EL&&Object.keys(EL.models).length>0,{timeout:60000});
 await page.getByRole('button',{name:'Navigation',exact:true}).click();
 assert.equal(await page.getByRole('button',{name:'Reset to north',exact:true}).isVisible(),true);
 assert.equal(await page.getByText('Two fingers / right drag — orbit',{exact:true}).count(),0);
 await page.getByRole('button',{name:'Reset to north',exact:true}).click();
 const pose=await page.evaluate(()=>EL.captureCamera('test'));
 assert.ok(Math.abs(pose.dir[0])<1e-5);assert.ok(Math.abs(pose.up[0])<1e-5);
 await page.mouse.move(800,400);await page.mouse.down({button:'right'});await page.mouse.move(900,440,{steps:8});await page.mouse.up({button:'right'});
 const right=await page.evaluate(()=>{const c=EL.viewer.camera;return [c.rightWC.x,c.rightWC.y,c.rightWC.z];});
 assert.ok(right.every(Number.isFinite));
 assert.deepEqual(errors,[]);
 await browser.close();console.log('viewer controls passed');
})().catch(e=>{console.error(e);process.exit(1);});
