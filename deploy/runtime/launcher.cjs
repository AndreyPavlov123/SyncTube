'use strict';
const fs = require('node:fs');
const {spawn} = require('node:child_process');
const {sweep} = require('./retention.cjs');
const root = '/app/user';
const retention = Number(process.env.UPLOAD_RETENTION_SECONDS);
fs.mkdirSync(root, {recursive:true});
// Seed only missing files. Persisted user accounts, configuration and uploads win.
fs.cpSync('/opt/synctube-user', root, {recursive:true, force:false, errorOnExist:false});
fs.copyFileSync('/etc/synctube/config.json', root + '/config.json');
sweep(root, retention);
const child = spawn(process.execPath, ['--require', '/app/deploy/runtime/http-timeout.cjs', 'build/server.js'], {cwd:'/app', stdio:'inherit'});
let maintenanceFailed = false;
const timer = setInterval(() => {
  try { sweep(root, retention); }
  catch {
    maintenanceFailed = true;
    console.error('Upload retention failed; stopping service');
    child.kill('SIGTERM');
  }
}, 60000);
for (const signal of ['SIGTERM','SIGINT']) process.on(signal, () => child.kill(signal));
child.on('error', () => {clearInterval(timer); process.exit(1);});
child.on('exit', (code, signal) => {
  clearInterval(timer);
  process.exit(maintenanceFailed ? 1 : (code ?? (signal === 'SIGTERM' ? 0 : 1)));
});
