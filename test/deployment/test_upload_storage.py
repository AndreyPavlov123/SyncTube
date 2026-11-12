"""Exercise the pinned, packaged server with real streams and abrupt process death."""
import http.client,json,shutil,socket,subprocess,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class UploadStorage(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.source=ROOT
 def setUp(self):
  self.temp_case=tempfile.TemporaryDirectory(prefix='synctube-stream-');self.addCleanup(self.temp_case.cleanup)
  self.root=Path(self.temp_case.name)
  for name in ['build','user']:shutil.copytree(self.source/name,self.root/name)
  for name in ['res','node_modules','default-config.json','deploy']:(self.root/name).symlink_to(self.source/name)
  with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
  (self.root/'user/config.json').write_text(json.dumps({'port':self.port,'cacheStorageLimitGiB':12288/(1024**3),'localAdmins':False}))
  self.proc=None;self.clients=[];self.addCleanup(self.cleanup)
  self.start();self.stop();self.start() # Establish a previous persisted room state.
 def cleanup(self):
  for c in self.clients:c.close()
  if self.proc and self.proc.poll() is None:self.stop()
 def start(self):
  self.proc=subprocess.Popen(['node','build/server.js'],cwd=self.root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(100):
   if self.proc.poll() is not None:raise RuntimeError('Packaged server exited')
   try:
    c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=1);c.request('GET','/');r=c.getresponse();r.read();c.close();return
   except OSError:time.sleep(.05)
  raise RuntimeError('Packaged server readiness timeout')
 def stop(self,kill=False):
  if kill:self.proc.kill()
  else:self.proc.terminate()
  self.proc.wait(timeout=10)
 def begin(self,name,size):
  c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5);self.clients.append(c)
  c.putrequest('POST','/upload');c.putheader('Content-Length',str(size));c.putheader('content-name',name);c.endheaders();return c
 def finish(self,c):
  r=c.getresponse();status=r.status;r.read();c.close();return status
 def test_acknowledged_upload_survives_sigkill_without_room_checkpoint(self):
  c=self.begin('complete.mp4',2048);c.send(b'a'*2048);self.assertEqual(self.finish(c),200)
  self.stop(kill=True);self.start()
  self.assertEqual((self.root/'user/res/cache/complete.mp4').read_bytes(),b'a'*2048)
 def test_concurrent_streams_reserve_full_sizes_and_release_on_abort(self):
  a=self.begin('a.mp4',8192);a.send(b'a'*1024);time.sleep(.1)
  b=self.begin('b.mp4',8192);b.send(b'b'*1024)
  self.assertEqual(self.finish(b),413)
  a.send(b'a'*7168);self.assertEqual(self.finish(a),200)
  self.assertLessEqual(sum(p.stat().st_size for p in (self.root/'user/res/cache').iterdir()),12288)
  c=self.begin('interrupted.mp4',8192);c.send(b'c'*1024);time.sleep(.1);c.close();time.sleep(.2)
  d=self.begin('next.mp4',8192);d.send(b'd'*8192);self.assertEqual(self.finish(d),200)
 def test_reused_filename_does_not_recover_partial_from_old_index(self):
  c=self.begin('reuse.mp4',2048);c.send(b'a'*2048);self.assertEqual(self.finish(c),200)
  (self.root/'user/res/cache/reuse.mp4').unlink() # Normal expiry can free the name.
  d=self.begin('reuse.mp4',8192);d.send(b'x'*1024);time.sleep(.1)
  self.stop(kill=True);d.close();self.start()
  self.assertFalse((self.root/'user/res/cache/reuse.mp4').exists())
 def test_packaging_uses_the_patch_and_storage_module(self):
  dockerfile=(ROOT/'Dockerfile').read_text()
  self.assertIn('COPY deploy/runtime ./deploy/runtime',dockerfile)
  self.assertNotIn('haxe:',dockerfile)
  self.assertIn('python3 -m unittest',dockerfile)
 def test_index_commit_failure_never_acknowledges_success(self):
  (self.root/'user/uploads.json.tmp').mkdir() # Force atomic checkpoint failure.
  c=self.begin('uncommitted.mp4',2048);c.send(b'x'*2048)
  try:status=self.finish(c)
  except (OSError,http.client.HTTPException):status=0
  self.assertNotEqual(status,200)
  self.assertEqual(self.proc.wait(timeout=5),1)
  (self.root/'user/uploads.json.tmp').rmdir()
  self.start()
  self.assertFalse((self.root/'user/res/cache/uncommitted.mp4').exists())
 def test_incomplete_upload_does_not_become_durable(self):
  c=self.begin('partial.mp4',8192);c.send(b'x'*1024);time.sleep(.1)
  self.stop(kill=True);c.close();self.start()
  self.assertFalse((self.root/'user/res/cache/partial.mp4').exists())
if __name__=='__main__':unittest.main()
