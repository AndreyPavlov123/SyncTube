"""Exercise deployed upload retention, including playlist-pinned files."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'deploy/runtime/retention.cjs'

class Retention(unittest.TestCase):
    def test_expiry_removes_old_upload_but_preserves_fresh_and_state(self):
        with tempfile.TemporaryDirectory() as temp:
            code = r'''
const fs = require('node:fs');
const path = require('node:path');
const {sweep} = require(process.argv[1]);
const root = process.argv[2];
fs.mkdirSync(path.join(root, 'res/cache'), {recursive:true});
fs.writeFileSync(path.join(root, 'res/cache/old.mp4'), 'old');
fs.writeFileSync(path.join(root, 'res/cache/new.mp4'), 'new');
fs.writeFileSync(path.join(root, 'state.json'), '{"cachedFiles":["old.mp4"]}');
const now = Date.now();
fs.utimesSync(path.join(root, 'res/cache/old.mp4'), new Date(0), new Date(0));
sweep(root, 14*86400, now);
console.log(JSON.stringify({old:fs.existsSync(path.join(root,'res/cache/old.mp4')),fresh:fs.existsSync(path.join(root,'res/cache/new.mp4')),state:fs.readFileSync(path.join(root,'state.json'),'utf8')}));
'''
            result = subprocess.run(['node','-e',code,str(SCRIPT),temp],check=True,capture_output=True,text=True)
            data = json.loads(result.stdout)
            self.assertFalse(data['old'])
            self.assertTrue(data['fresh'])
            self.assertEqual(json.loads(data['state']), {'cachedFiles':['old.mp4']})

    def test_crash_reports_have_age_count_and_size_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            code = r"""
const fs=require('node:fs'),path=require('node:path');
const {sweep}=require(process.argv[1]);const root=process.argv[2];
const folder=path.join(root,'crashes');fs.mkdirSync(folder,{recursive:true});
const now=Date.now();
for(let i=0;i<22;i++) {const file=path.join(folder,'crash-'+i+'.txt');fs.writeFileSync(file,'debug');fs.utimesSync(file,new Date(now-i*1000),new Date(now-i*1000));}
fs.writeFileSync(path.join(folder,'oversized.txt'),Buffer.alloc(262145));
fs.writeFileSync(path.join(folder,'expired.txt'),'old');fs.utimesSync(path.join(folder,'expired.txt'),new Date(0),new Date(0));
sweep(root,14*86400,now);
const files=fs.readdirSync(folder);
if(files.length!==10 || files.includes('expired.txt') || files.includes('oversized.txt') || !files.includes('crash-0.txt'))process.exit(1);
"""
            subprocess.run(['node','-e',code,str(SCRIPT),temp],check=True)

    def test_refuses_symlinks_and_invalid_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            code = r'''
const fs = require('node:fs'); const path = require('node:path');
const {sweep} = require(process.argv[1]); const root = process.argv[2];
fs.mkdirSync(path.join(root,'res/cache'),{recursive:true});
fs.writeFileSync(path.join(root,'outside'), 'keep');
fs.symlinkSync(path.join(root,'outside'),path.join(root,'res/cache/evil.mp4'));
let failed=0; for (const seconds of [0,-1,NaN,14*86400]) {try {sweep(root,seconds,Date.now());} catch {failed++;}}
if (failed !== 4 || fs.readFileSync(path.join(root,'outside'),'utf8') !== 'keep') process.exit(1);
'''
            subprocess.run(['node','-e',code,str(SCRIPT),temp],check=True)

if __name__ == '__main__': unittest.main()
