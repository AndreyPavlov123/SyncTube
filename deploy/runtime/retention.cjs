'use strict';
const fs = require('node:fs');
const path = require('node:path');
// Playlist entries evade upstream cache eviction. Expire the actual upload files
// independently so pinning a playlist cannot turn this cache into unbounded storage.
function trimCrashReports(root, cutoff) {
  const folder = path.join(root, 'crashes');
  if (!fs.existsSync(folder)) return;
  const kept = [];
  for (const entry of fs.readdirSync(folder, {withFileTypes:true})) {
    const file = path.join(folder, entry.name), stat = fs.lstatSync(file);
    if (!entry.isFile() || !stat.isFile()) throw new Error('unexpected crash report entry');
    // Upstream writes a new report on every uncaught exception. Bound the live
    // debug set independently of upload eviction and the ordinary log rotation.
    if (stat.mtimeMs < cutoff || stat.size > 256 * 1024) fs.unlinkSync(file);
    else kept.push({file, modified:stat.mtimeMs});
  }
  kept.sort((a,b) => b.modified - a.modified || a.file.localeCompare(b.file));
  for (const report of kept.slice(10)) fs.unlinkSync(report.file);
}
function sweep(root, seconds, now = Date.now()) {
  if (!Number.isSafeInteger(seconds) || seconds <= 0) throw new Error('invalid retention');
  const cache = path.join(root, 'res/cache');
  fs.mkdirSync(cache, {recursive: true});
  const cutoff = now - seconds * 1000;
  for (const entry of fs.readdirSync(cache, {withFileTypes: true})) {
    if (!entry.isFile()) throw new Error('unexpected non-file in upload cache');
    const file = path.join(cache, entry.name);
    const stat = fs.lstatSync(file);
    if (!stat.isFile()) throw new Error('upload cache entry changed type');
    if (stat.mtimeMs < cutoff) fs.unlinkSync(file);
  }
  trimCrashReports(root, cutoff);
}
module.exports = {sweep};
