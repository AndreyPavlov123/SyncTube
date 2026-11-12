'use strict';
const fs = require('node:fs');
const path = require('node:path');
// Playlist entries evade upstream cache eviction. Expire the actual upload files
// independently so pinning a playlist cannot turn this cache into unbounded storage.
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
}
module.exports = {sweep};
