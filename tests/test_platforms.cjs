const assert=require('node:assert/strict');
const path=require('node:path');
const {runtimePaths}=require('../scripts/platform.cjs');
const root=path.resolve('directory with spaces');
assert.equal(runtimePaths(root,'win32').python,path.join(root,'.venv','Scripts','python.exe'));
assert.equal(runtimePaths(root,'darwin').python,path.join(root,'.venv','bin','python3'));
assert.equal(runtimePaths(root,'darwin').setup,'bash scripts/setup.sh');
console.log('PASS: Windows and macOS runtime paths.');
