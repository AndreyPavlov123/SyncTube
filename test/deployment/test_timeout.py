"""Real slow-body requests verify the deployment adapter's server timeout."""
from pathlib import Path
import json, os, subprocess, unittest
ROOT=Path(__file__).resolve().parents[2]
class Timeout(unittest.TestCase):
 def test_slow_body_and_negative_control(self):
  script=r'''
const http=require('node:http');const assert=require('node:assert/strict');
const enable=process.argv[1]==='enable';
if(enable){process.env.HTTP_REQUEST_TIMEOUT_MS='2000';require(process.argv[2]);}
const server=http.createServer({requestTimeout:200,headersTimeout:100,connectionsCheckingInterval:10},(req,res)=>{req.resume();req.on('end',()=>res.end('complete'));});
server.listen(0,'127.0.0.1',()=>{
 const req=http.request({host:'127.0.0.1',port:server.address().port,method:'POST',headers:{'Content-Length':'6'}},res=>{res.resume();res.on('end',()=>{console.log(JSON.stringify({status:res.statusCode,timeout:server.requestTimeout}));server.close();});});
 req.on('error',()=>{console.log(JSON.stringify({status:0}));server.close();});
 req.write('a');setTimeout(()=>req.end('bcdef'),700);
});
'''
  for enabled,status in [('disable',408),('enable',200)]:
   result=subprocess.run(['node','-e',script,enabled,str(ROOT/'deploy/runtime/http-timeout.cjs')],text=True,capture_output=True,timeout=10,check=True)
   data=json.loads(result.stdout)
   self.assertEqual(data['status'],status)
   if enabled=='enable':self.assertEqual(data['timeout'],2000)
 def test_invalid_budget_fails_closed(self):
  for value in ['', '0', '-1', '86400001', 'NaN']:
   result=subprocess.run(['node','--require',str(ROOT/'deploy/runtime/http-timeout.cjs'),'-e','process.exit(0)'],env={**os.environ,'HTTP_REQUEST_TIMEOUT_MS':value},capture_output=True,timeout=10)
   self.assertNotEqual(result.returncode,0,value)
 def test_adapter_is_packaged_and_loaded(self):
  self.assertIn('COPY deploy/runtime ./deploy/runtime',(ROOT/'Dockerfile').read_text())
  self.assertIn("['--require', '/app/deploy/runtime/http-timeout.cjs', 'build/server.js']",(ROOT/'deploy/runtime/launcher.cjs').read_text())
if __name__=='__main__':unittest.main()
