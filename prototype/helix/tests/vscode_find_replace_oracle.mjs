#!/usr/bin/env node
// Execute pinned upstream TypeScript, with only its imports wired by this
// harness. Expectations are produced by VS Code, never by the Rust port.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {stripTypeScriptTypes} from 'node:module';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const cache=process.argv[2];
if (!cache) throw Error('Usage: vscode_find_replace_oracle.mjs REFERENCE_DIR [--fetch] [--write]');
const manifest=JSON.parse(fs.readFileSync(path.join(here,'../docs/vscode-reference-manifest.json')));
fs.mkdirSync(cache,{recursive:true});
const sources=[];
for (const key of ['charCode','preserveCase','replacePattern']) {
 const ref=manifest.sources.find(x=>x.key===key);const file=path.join(cache,key+'.ts');
 if (process.argv.includes('--fetch')) {
  const response=await fetch(`https://raw.githubusercontent.com/microsoft/vscode/${ref.revision}/${ref.path}`);
  if (!response.ok) throw Error(`${key}: HTTP ${response.status}`);
  fs.writeFileSync(file,Buffer.from(await response.arrayBuffer()));
 }
 const data=fs.readFileSync(file);
 if (createHash('sha256').update(data).digest('hex')!==ref.sha256) throw Error(`${key}: source hash mismatch`);
 sources.push(data.toString().replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,''));
}
const stringsRef=manifest.sources.find(x=>x.key==='strings');
if (process.argv.includes('--fetch')) {
 const response=await fetch(`https://raw.githubusercontent.com/microsoft/vscode/${stringsRef.revision}/${stringsRef.path}`);
 if (!response.ok) throw Error(`strings: HTTP ${response.status}`);
 fs.writeFileSync(path.join(cache,'strings.ts'),Buffer.from(await response.arrayBuffer()));
}
const stringsData=fs.readFileSync(path.join(cache,'strings.ts'));
if (createHash('sha256').update(stringsData).digest('hex')!==stringsRef.sha256) throw Error('strings: source hash mismatch');
const contains=stringsData.toString().match(/export function containsUppercaseCharacter[\s\S]*?\n}/)[0].replace('export ','');
const code=stripTypeScriptTypes(contains+'\nconst strings={containsUppercaseCharacter};\n'+sources.join('\n')+'\nglobalThis.oracle={parseReplaceString,ReplacePattern};',{mode:'transform'});
const context=vm.createContext({});vm.runInContext(code,context);
const casesFile=path.join(here,'find-replace-cases.json');const cases=JSON.parse(fs.readFileSync(casesFile));
for (const item of cases) {
 const pattern=item.regex?context.oracle.parseReplaceString(item.pattern):context.oracle.ReplacePattern.fromStaticValue(item.pattern);
 const actual=pattern.buildReplaceString(item.groups,item.preserve);
 if (process.argv.includes('--write')) item.expected=actual;
 else if (actual!==item.expected) throw Error(`${item.name}: fixture differs from upstream: ${JSON.stringify(actual)}`);
}
if (process.argv.includes('--write')) fs.writeFileSync(casesFile,JSON.stringify(cases,null,2)+'\n');
console.log(JSON.stringify({revision:manifest.revision,cases:cases.length,verified:true}));
