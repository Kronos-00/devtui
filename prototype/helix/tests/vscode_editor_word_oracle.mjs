#!/usr/bin/env node
// Execute the pinned upstream word-selection implementation with record-only
// cursor state and a one-line model. The algorithm and classifier are upstream.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {stripTypeScriptTypes} from 'node:module';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const cache=process.argv[2];
if (!cache) throw Error('Usage: vscode_editor_word_oracle.mjs REFERENCE_DIR [--fetch] [--write]');
const manifest=JSON.parse(fs.readFileSync(path.join(here,'../docs/vscode-reference-manifest.json')));
const keys=['uint','charCode','characterClassifier','wordCharacterClassifier','cursorWordOperations','wordHelper'];
fs.mkdirSync(cache,{recursive:true});
const sources=[];
for (const key of keys) {
  const ref=manifest.sources.find(x=>x.key===key);
  const file=path.join(cache,key+'.ts');
  if (process.argv.includes('--fetch')) {
    const response=await fetch(`https://raw.githubusercontent.com/microsoft/vscode/${ref.revision}/${ref.path}`);
    if (!response.ok) throw Error(`${key}: HTTP ${response.status}`);
    fs.writeFileSync(file,Buffer.from(await response.arrayBuffer()));
  }
  const data=fs.readFileSync(file);
  if (createHash('sha256').update(data).digest('hex')!==ref.sha256) throw Error(`${key}: source hash mismatch`);
  if (key!=='wordHelper') sources.push(data.toString().replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,''));
}
const helperRef=manifest.sources.find(x=>x.key==='wordHelper');
const helperData=fs.readFileSync(path.join(cache,'wordHelper.ts'));
if (createHash('sha256').update(helperData).digest('hex')!==helperRef.sha256) throw Error('wordHelper: source hash mismatch');
const defaultLine=helperData.toString().split('\n').find(x=>x.startsWith('export const USUAL_WORD_SEPARATORS'));
const harness=`
class LRUCache extends Map { constructor() { super(); } }
class Position { constructor(lineNumber,column) { this.lineNumber=lineNumber; this.column=column; } }
class Range { constructor(startLineNumber,startColumn,endLineNumber,endColumn) { Object.assign(this,{startLineNumber,startColumn,endLineNumber,endColumn}); } }
class SingleCursorState { constructor(selectionStart,kind,leftover,position) { this.selectionStart=selectionStart; this.position=position; } }
const SelectionStartKind={Word:1};
${defaultLine.replace('export ','')}
`;
const code=stripTypeScriptTypes(harness+sources.join('\n')+'\nglobalThis.oracle={WordOperations,Position,USUAL_WORD_SEPARATORS};',{mode:'transform'});
const context=vm.createContext({});vm.runInContext(code,context);
const {WordOperations,Position,USUAL_WORD_SEPARATORS}=context.oracle;
const file=path.join(here,'editor-word-cases.json');
const cases=JSON.parse(fs.readFileSync(file));
for (const item of cases) {
  const column=Array.from(item.text).slice(0,item.click_char).join('').length+1;
  const model={getLineContent:()=>item.text,getLineMaxColumn:()=>item.text.length+1};
  const state=WordOperations.word({wordSeparators:USUAL_WORD_SEPARATORS,wordSegmenterLocales:[]},model,null,false,new Position(1,column));
  const range=state.selectionStart;
  const expected=item.text.slice(range.startColumn-1,range.endColumn-1);
  if (process.argv.includes('--write')) item.expected=expected;
  else if (item.expected!==expected) throw Error(`${item.name}: fixture differs from upstream`);
}
if (process.argv.includes('--write')) fs.writeFileSync(file,JSON.stringify(cases,null,2)+'\n');
console.log(JSON.stringify({revision:manifest.revision,cases:cases.length,verified:true}));
