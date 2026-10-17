#!/usr/bin/env node
// Execute pinned Microsoft VS Code layout2d and Range namespace (MIT license).
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {stripTypeScriptTypes} from 'node:module';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const here=path.dirname(fileURLToPath(import.meta.url));
const reference=process.argv[2];
if (!reference) throw new Error('Usage: node vscode_context_menu_oracle.mjs REFERENCE_DIR [--fetch] [--write]');
const manifest=JSON.parse(fs.readFileSync(path.join(here,'../docs/vscode-reference-manifest.json')));
const context=vm.createContext({});
for (const [key,filename] of [['layoutRange','range-anchor.ts'],['contextMenuLayout','layout-anchor.ts']]) {
 const entry=manifest.sources.find(e=>e.key===key);
 const file=path.join(reference,filename);
 if (process.argv.includes('--fetch')) {
  fs.mkdirSync(reference,{recursive:true});
  const response=await fetch(`https://raw.githubusercontent.com/microsoft/vscode/${entry.revision}/${entry.path}`);
  if(!response.ok) throw new Error(`${key}: HTTP ${response.status}`);
  const bytes=Buffer.from(await response.arrayBuffer());
  assert.equal(createHash('sha256').update(bytes).digest('hex'),entry.sha256);
  fs.writeFileSync(file,bytes);
 }
 const raw=fs.readFileSync(file);
 assert.equal(createHash('sha256').update(raw).digest('hex'),entry.sha256);
 const source=raw.toString().replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,'');
 vm.runInContext(stripTypeScriptTypes(source,{mode:'transform'}),context);
}
const file=path.join(here,'context-menu-cases.json');
const stored=JSON.parse(fs.readFileSync(file));
context.input=stored.map(({expected,...c})=>c);
const actual=vm.runInContext(`input.map(c=>{
 const [width,height]=c.viewport;
 // A terminal mouse location is one cell. Resize clamps an old location to the
 // new visible bounds before handing the anchor to the upstream layout code.
 const anchor={left:Math.min(c.anchor[0],width-1),top:Math.min(c.anchor[1],height-1),width:1,height:1};
 const result=layout2d({left:0,top:0,width,height},{width:c.menu[0],height:c.menu[1]},anchor);
 return {...c,expected:[result.left,result.top]};
})`,context);
if(process.argv.includes('--write')) fs.writeFileSync(file,JSON.stringify(actual,null,2)+'\n');
else assert.equal(JSON.stringify(actual),JSON.stringify(stored));
console.log(JSON.stringify({revision:manifest.revision,cases:actual.length,verified:true}));
