#!/usr/bin/env node
// Run the pinned MIT-licensed Microsoft VS Code algorithms, not a reimplementation.
// Pass a directory containing the hash-verified reference .ts files. Node >= 24.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { createHash } from 'node:crypto';
import { stripTypeScriptTypes } from 'node:module';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const here = path.dirname(fileURLToPath(import.meta.url));
const reference = process.argv[2];
if (!reference) throw new Error('Usage: node vscode_column_oracle.mjs REFERENCE_DIR [--write]');
const manifest = JSON.parse(fs.readFileSync(path.join(here, '../docs/vscode-reference-manifest.json')));
if (process.argv.includes('--fetch')) {
  fs.mkdirSync(reference, {recursive:true});
  const names = ['charCode','uint','lazy','strings','cursorColumns','cursorColumnSelection','cursorDeleteOperations','viewModelImpl'];
  for (const name of names) {
    const entry = manifest.sources.find(item => item.key === name);
    const url = `https://raw.githubusercontent.com/microsoft/vscode/${entry.revision}/${entry.path}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${name}: HTTP ${response.status}`);
    const data = Buffer.from(await response.arrayBuffer());
    assert.equal(createHash('sha256').update(data).digest('hex'), entry.sha256);
    fs.writeFileSync(path.join(reference, name+'.ts'), data);
  }
}
const context = vm.createContext({});
function read(name) {
  const entry = manifest.sources.find(item => item.key === name);
  const raw = fs.readFileSync(path.join(reference, name + '.ts'));
  assert.equal(createHash('sha256').update(raw).digest('hex'), entry.sha256, name + ' source hash');
  return raw.toString();
}
function compile(source) {
  return stripTypeScriptTypes(source.replace(/^import .*;\r?\n/gm, '').replace(/\bexport /g, ''), {mode:'transform'});
}
function run(source) { return vm.runInContext(compile(source), context); }
// The string module's unrelated ambiguous-character cache only needs a holder.
run('class LRUCachedFunction { constructor(fn) { this.fn = fn; } get(arg) { return this.fn(arg); } }');
for (const name of ['charCode', 'uint', 'lazy']) run(read(name));
run(read('strings') + '\nglobalThis.strings = {GraphemeIterator, CodePointIterator, getNextCodePoint, isFullWidthCharacter, isEmojiImprecise};');
run(read('cursorColumns'));
// Data-container adapters; all selection, width, copy and cut algorithms below
// are executed verbatim from the pinned upstream sources.
run(`class Position {
 constructor(lineNumber,column) { Object.assign(this,{lineNumber,column}); }
 static compare(a,b) { return a.lineNumber-b.lineNumber || a.column-b.column; }
}
class Range {
 constructor(startLineNumber,startColumn,endLineNumber,endColumn) { Object.assign(this,{startLineNumber,startColumn,endLineNumber,endColumn}); }
 isEmpty() { return this.startLineNumber===this.endLineNumber && this.startColumn===this.endColumn; }
 getStartPosition() { return new Position(this.startLineNumber,this.startColumn); }
 getEndPosition() { return new Position(this.endLineNumber,this.endColumn); }
 getPosition() { return this.getEndPosition(); }
 static compareRangesUsingStarts(a,b) { return Position.compare(a.getStartPosition(),b.getStartPosition()); }
}
class SingleCursorState {
 constructor(selectionStart,kind,leftover,position) { Object.assign(this,{selectionStart,position}); }
}
class ReplaceCommand { constructor(range,text) { Object.assign(this,{range,text}); } }
class EditOperationResult { constructor(type,commands) { this.commands=commands; } }
const SelectionStartKind={Simple:0};
const EditOperationType={Other:0};
const EndOfLinePreference={CRLF:0,TextDefined:1};`);
run(read('cursorColumnSelection'));
run(read('cursorDeleteOperations'));
const modelSource = read('viewModelImpl');
const copyStart = modelSource.indexOf('\tpublic getPlainTextToCopy(');
const copyEnd = modelSource.indexOf('\n\tpublic getRichTextToCopy(', copyStart);
assert.ok(copyStart >= 0 && copyEnd > copyStart);
run('class CopyModel { ' + modelSource.slice(copyStart, copyEnd) + ' }');
const caseFile = path.join(here, 'column-selection-cases.json');
const stored = JSON.parse(fs.readFileSync(caseFile));
context.input = stored.map(({selection, clipboard, cut, ...input}) => input);
const actual = vm.runInContext(`input.map(c => {
 const lines = c.newline === false ? c.lines : [...c.lines, ''];
 const model = {
  getLineCount: () => lines.length,
  getLineMinColumn: () => 1,
  getLineMaxColumn: n => lines[n-1].length+1,
  getEOL: () => '\\n',
  getValueInRange: r => r.startLineNumber === r.endLineNumber
   ? lines[r.startLineNumber-1].slice(r.startColumn-1,r.endColumn-1)
   : [lines[r.startLineNumber-1].slice(r.startColumn-1), ...lines.slice(r.startLineNumber,r.endLineNumber-1), lines[r.endLineNumber-1].slice(0,r.endColumn-1)].join('\\n')
 };
 const config = {
  emptySelectionClipboard: true,
  columnFromVisibleColumn: (m,n,v) => CursorColumns.columnFromVisibleColumn(lines[n-1],v,c.tabSize??4),
  visibleColumnFromColumn: (m,p) => CursorColumns.visibleColumnFromColumn(lines[p.lineNumber-1],p.column,c.tabSize??4)
 };
 const result = ColumnSelection.columnSelect(config,model,c.fromRow??1,c.from,c.toRow??c.lines.length,c.to);
 const ranges = result.viewStates.map(s => new Range(s.position.lineNumber,Math.min(s.selectionStart.startColumn,s.position.column),s.position.lineNumber,Math.max(s.selectionStart.startColumn,s.position.column)));
 const copy = new CopyModel(); copy.model = model;
 const {sourceText} = copy.getPlainTextToCopy(ranges, true, false);
 let cut = lines.join('\\n');
 const offset = (line,col) => lines.slice(0,line-1).reduce((sum,l)=>sum+l.length+1,0)+col-1;
 const edits = DeleteOperations.cut(config,model,ranges).commands.filter(Boolean).map(({range,text})=>({start:offset(range.startLineNumber,range.startColumn),end:offset(range.endLineNumber,range.endColumn),text})).sort((a,b)=>b.start-a.start);
 for (const e of edits) cut=cut.slice(0,e.start)+e.text+cut.slice(e.end);
 return {...c,selection:result.viewStates.map(s=>({row:s.position.lineNumber,anchor:s.selectionStart.startColumn,head:s.position.column,text:model.getValueInRange(new Range(s.position.lineNumber,Math.min(s.selectionStart.startColumn,s.position.column),s.position.lineNumber,Math.max(s.selectionStart.startColumn,s.position.column)))})),clipboard:Array.isArray(sourceText)?sourceText.join('\\n'):sourceText,cut};
})`, context);
if (process.argv.includes('--write')) {
 fs.writeFileSync(caseFile, JSON.stringify(actual,null,2)+'\n');
} else {
 assert.equal(JSON.stringify(actual), JSON.stringify(stored));
}
console.log(JSON.stringify({revision:manifest.revision,cases:actual.length,verified:true}));
