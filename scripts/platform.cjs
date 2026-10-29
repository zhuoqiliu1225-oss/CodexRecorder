const path=require('node:path');
function runtimePaths(root,platform=process.platform){return {
 python:path.join(root,'.venv',...(platform==='win32'?['Scripts','python.exe']:['bin','python3'])),
 setup:platform==='win32'?'scripts/setup.ps1':'bash scripts/setup.sh'
};}
module.exports={runtimePaths};
