import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync, statSync} from 'node:fs';

const css = readFileSync(new URL('../../static/frontend_v1/css/calm.css', import.meta.url), 'utf8');
const tokens = readFileSync(new URL('../../static/frontend_v1/css/tokens.css', import.meta.url), 'utf8');
const clean = css.replace(/\/\*[\s\S]*?\*\//g, '').trim();

test('calm stylesheet is token-only and scoped to the opt-in document class', () => {
  const blocks=[...clean.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
  assert.equal(blocks.length,2);
  assert.deepEqual(blocks.map(match=>match[1].trim()),['.s-calm','.s-calm[data-theme="dark"]']);
  for (const [,selector,body] of blocks) {
    assert.match(selector.trim(),/^\.s-calm(?:\[data-theme="dark"\])?$/);
    for (const declaration of body.split(';').map(item=>item.trim()).filter(Boolean)) {
      assert.match(declaration,/^--az-[a-z0-9-]+\s*:/,declaration);
    }
  }
  assert.doesNotMatch(clean,/@import|url\(|https?:|\b(?:body|main|button|input|header|footer)\b/i);
});

test('calm uses the accepted light/dark palette, type scale and dimensions', () => {
  for (const value of ['#1d57d8','#17459f','#ffffff','#1f1f1f','#c4c7c5','#137333','#8f4e00',
                       '#131314','#1b1c1e','#26282b','#8ab4f8','#aecbfa','#0b1d3f',
                       '#81c995','#fdd663']) {
    assert.ok(css.includes(value),value);
  }
  for (const declaration of ['--az-text-sm: .8125rem','--az-text-md: .9375rem','--az-text-2xl: 1.625rem',
                              '--az-radius: .75rem','--az-radius-lg: 1rem','--az-sidebar: 14.5rem']) {
    assert.ok(css.includes(declaration),declaration);
  }
  const media=[...css.matchAll(/(?:min|max)-width\s*:\s*([\d.]+)(px|rem)/g)].map(match=>
    match[2]==='rem' ? Number(match[1])*16 : Number(match[1]));
  assert.ok(media.every(value=>value===560||value===900),media);
});

test('tokens declare exactly the three vendored Figtree weights with swap', () => {
  const faces=[...tokens.matchAll(/@font-face\s*\{([\s\S]*?)\}/g)].map(match=>match[1]);
  assert.equal(faces.length,3);
  assert.deepEqual(faces.map(face=>Number(face.match(/font-weight:\s*(\d+)/)?.[1])),[400,500,600]);
  for (const [face,file] of faces.map((face,index)=>[face,['Regular','Medium','SemiBold'][index]])) {
    assert.match(face,new RegExp(`Figtree-${file}\\.woff2`));
    assert.match(face,/font-display:\s*swap/);
    assert.match(face,/format\("woff2"\)/);
  }
});

test('official font assets stay pinned and within the three-weight budget', () => {
  const expected={
    'Figtree-Regular.woff2':'72de3fc98fde5a540d729ddca05c035e0b0e444c4ee5f4e0a8c30220e4406c93',
    'Figtree-Medium.woff2':'da1916212ef66e1ed93cd9fa00a1954874daf92f7ae5a99309e77c35d986a588',
    'Figtree-SemiBold.woff2':'b1e611e9d3d8ce9e9695a9af5edb7085087f959fe1dd107846ad9d454dbe7c5e',
  };
  let bytes=0;
  for (const [name,digest] of Object.entries(expected)) {
    const url=new URL(`../../static/frontend_v1/fonts/${name}`,import.meta.url), data=readFileSync(url);
    bytes+=statSync(url).size;
    assert.equal(createHash('sha256').update(data).digest('hex'),digest,name);
  }
  assert.ok(bytes<=71000,bytes);
  assert.match(readFileSync(new URL('../../static/frontend_v1/fonts/OFL.txt',import.meta.url),'utf8'),/SIL OPEN FONT LICENSE Version 1\.1/);
});
