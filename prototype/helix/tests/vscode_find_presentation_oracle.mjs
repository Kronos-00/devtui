#!/usr/bin/env node
// Read the actual upstream decoration options, CSS binding and registered
// color defaults. The terminal tests use this source-derived reference.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const cache=process.argv[2];
if (!cache) throw Error('Usage: vscode_find_presentation_oracle.mjs CACHE [--fetch] [--write]');
const manifest=JSON.parse(fs.readFileSync(path.join(here,'../docs/vscode-reference-manifest.json')));
const keys=['findDecorations','findWidgetCss','editorThemeColors'];const source={};
fs.mkdirSync(cache,{recursive:true});
for (const key of keys) {
 const ref=manifest.sources.find(item=>item.key===key);
 const file=path.join(cache,key+(ref.path.endsWith('.css')?'.css':'.ts'));
 if (process.argv.includes('--fetch')) {
  const response=await fetch(`https://raw.githubusercontent.com/microsoft/vscode/${ref.revision}/${ref.path}`);
  if (!response.ok) throw Error(`${key}: HTTP ${response.status}`);
  fs.writeFileSync(file,Buffer.from(await response.arrayBuffer()));
 }
 const data=fs.readFileSync(file);
 if (createHash('sha256').update(data).digest('hex')!==ref.sha256) throw Error(`${key}: hash mismatch`);
 source[key]=data.toString();
}
const options=source.findDecorations.match(/private static readonly _FIND_SCOPE_DECORATION = ModelDecorationOptions\.register\(([\s\S]*?)\);/)[1];
const scope=vm.runInNewContext('('+options+')');
const declaration=source.editorThemeColors.match(/export const editorFindRangeHighlight = ([\s\S]*?);/)[1];
const color=vm.runInNewContext(declaration,{registerColor:(name,defaults)=>({name,defaults}),nls:{localize:()=>''}});
const css=source.findWidgetCss.match(/\.monaco-editor \.findScope\s*\{([^}]+)\}/)[1];
if (!css.includes(`var(--vscode-${color.name.replaceAll('.','-')})`)) throw Error('Scope CSS uses a different color');
const reference={revision:manifest.revision,sources:keys,isWholeLine:scope.isWholeLine,className:scope.className,colorName:color.name,dark:color.defaults.dark,light:color.defaults.light};
const file=path.join(here,'find-presentation-reference.json');
if (process.argv.includes('--write')) fs.writeFileSync(file,JSON.stringify(reference,null,2)+'\n');
else if (JSON.stringify(JSON.parse(fs.readFileSync(file)))!==JSON.stringify(reference)) throw Error('Presentation reference differs from upstream');
console.log(JSON.stringify({revision:manifest.revision,whole_line:reference.isWholeLine,dark:reference.dark,light:reference.light,verified:true}));
