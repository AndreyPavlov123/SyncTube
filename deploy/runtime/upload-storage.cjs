'use strict';
const fs = require('node:fs');
const path = require('node:path');
// Commit data/index before acknowledging uploads. Rename + directory fsync also
// avoids leaving a truncated index if a process/node dies during checkpointing.
function atomicWrite(file, data) {
  const temp = file + '.tmp';
  const fd = fs.openSync(temp, 'w', 0o600);
  try { fs.writeFileSync(fd, data); fs.fsyncSync(fd); }
  finally { fs.closeSync(fd); }
  fs.renameSync(temp, file);
  const directory = fs.openSync(path.dirname(file), 'r');
  try { fs.fsyncSync(directory); } finally { fs.closeSync(directory); }
}
class UploadStorage {
  constructor(cache) {
    this.cache = cache;
    this.index = path.join(cache, '../../uploads.json');
    this.reservations = new Map();
  }
  reserve(name, size) {
    if (!Number.isSafeInteger(size) || size < 0 || this.reservations.has(name)) throw new Error('Invalid upload reservation');
    this.reservations.set(name, size);
  }
  release(name) { this.reservations.delete(name); }
  reserved(name) { return this.reservations.has(name); }
  reservedSize(name) { return this.reservations.get(name); }
  completed(names) { return names.filter(name => !this.reserved(name)); }
  record(name) {
    if (typeof name !== 'string' || name !== path.basename(name) || name.startsWith('.')) throw new Error('Invalid cached filename');
    try {
      const stat = fs.lstatSync(path.join(this.cache, name), {bigint:true});
      if (!stat.isFile()) throw new Error('Non-file in upload cache');
      return {name, size:String(stat.size), inode:String(stat.ino), modified:String(stat.mtimeNs)};
    } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
  }
  recover(names) {
    if (!fs.existsSync(this.index)) {
      // Migrate the old room index once, before any upload can be admitted.
      const records = names.map(name => this.record(name)).filter(Boolean);
      atomicWrite(this.index, JSON.stringify(records));
      return records.map(record => record.name);
    }
    const journal = JSON.parse(fs.readFileSync(this.index, 'utf8'));
    if (!Array.isArray(journal)) throw new Error('Invalid completed-upload index');
    // A deleted filename can be reused by an interrupted upload. Match the
    // completed file identity, not merely its name or presence on disk.
    return journal.filter(expected => {
      const actual = this.record(expected.name);
      return actual && actual.size === expected.size && actual.inode === expected.inode && actual.modified === expected.modified;
    }).map(record => record.name);
  }
  complete(name, names) {
    const fd = fs.openSync(path.join(this.cache, name), 'r');
    try { fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    const directory = fs.openSync(this.cache, 'r');
    try { fs.fsyncSync(directory); } finally { fs.closeSync(directory); }
    // A reservation remains until this commit finishes, so other in-progress
    // streams never enter the durable index or a graceful room-state save.
    const completed = this.completed(names).concat(name);
    const records = [...new Set(completed)].map(n => this.record(n)).filter(Boolean);
    atomicWrite(this.index, JSON.stringify(records));
  }
}
module.exports = {UploadStorage, atomicWrite};
