import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { searchRecords, markdownHTML, serviceBase, validCatalog } from '../docs/lib.mjs';
const catalog=JSON.parse(fs.readFileSync(new URL('../docs/catalog.json',import.meta.url),'utf8'));
test('full catalog, search aliases, symptoms, typos and no matches',()=>{
 assert.ok(validCatalog(catalog));
 for(const [query,id] of [['媽媽手',15],['PFPS',31],['ＰＦＰＳ',31],['早上 腳底',41],['網球軸',13],['plantar fascitis',41],['50',50]])assert.equal(searchRecords(catalog.syndromes,query)[0].id,id,query);
 assert.equal(searchRecords(catalog.syndromes,'').length,50);
 assert.equal(searchRecords(catalog.syndromes,'zzzzzzzzzz').length,0);
 assert.equal(searchRecords(catalog.syndromes,'!!!').length,0);
 assert.equal(validCatalog({...catalog,syndromes:catalog.syndromes.slice(1)}),false);
});
test('model output renders as escaped text with supported Markdown',()=>{
 const rendered=markdownHTML('## 話術\n<script>alert(1)</script>\n- **重點**\n<img src=x onerror=alert(1)>');
 assert.match(rendered,/<h2>話術<\/h2>/);assert.match(rendered,/<strong>重點<\/strong>/);
 assert.ok(!rendered.includes('<script>'));assert.ok(!rendered.includes('<img'));assert.match(rendered,/&lt;script&gt;/);
});
test('API origin supports subpaths and HTTPS only outside localhost',()=>{
 assert.equal(serviceBase('','https://example.com/project/index.html'),'https://example.com/project/');
 assert.equal(serviceBase('https://api.example.com/clinic','https://example.com/'),'https://api.example.com/clinic/');
 assert.equal(serviceBase('http://127.0.0.1:8000','https://example.com/'),'http://127.0.0.1:8000/');
 for(const value of ['javascript:alert(1)','http://unsafe.example.com','https://user:secret@example.com','https://example.com/?secret=a'])assert.throws(()=>serviceBase(value,'https://example.com/'));
});
test('install manifest and PNG dimensions work under a GitHub Pages subpath',()=>{
 const base='https://foxicall.github.io/Physiotherapy_consultation/';
 const manifest=JSON.parse(fs.readFileSync(new URL('../docs/manifest.webmanifest',import.meta.url),'utf8'));
 assert.equal(new URL(manifest.scope,base).href,base);assert.ok(new URL(manifest.start_url,base).href.startsWith(base));assert.equal(manifest.display,'standalone');
 for(const icon of manifest.icons){const buffer=fs.readFileSync(new URL('../docs/'+icon.src,import.meta.url));const [width,height]=icon.sizes.split('x').map(Number);assert.equal(buffer.readUInt32BE(16),width);assert.equal(buffer.readUInt32BE(20),height);}
});
