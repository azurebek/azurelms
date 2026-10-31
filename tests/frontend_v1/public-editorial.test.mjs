// PUBLIC-02 tizim qoidalari (prototip `playground/Thirteenth Trial/verify.mjs` → CI).
// Maqsad: har yangi editorial sahifa yoki pattern improvizatsiya bilan dizayn tizimini buzmasin —
// yangi narsa faqat mavjud tokenlardan, faqat production breakpoint'larida, boshqa komponentga tegmasdan.
import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync, readdirSync} from 'node:fs';

const root = new URL('../../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const stripComments = css => css.replace(/\/\*[\s\S]*?\*\//g, '');
const EDITORIAL = 'static/frontend_v1/css/public-editorial.css';
const editorial = read(EDITORIAL);
const tokensCss = stripComments(read('static/frontend_v1/css/tokens.css'));
const TOKENS = new Set([...tokensCss.matchAll(/(--az-[a-z0-9-]+)\s*:/g)].map(match => match[1]));
const classesIn = css => new Set([...css.replace(/\{[^{}]*\}/g, '{}').matchAll(/\.(-?[a-z_][a-z0-9_-]*)/gi)].map(match => match[1]));
// Boshqa V1 fayllaridagi klasslar — editorial ular uchun selector yozmaydi (cascade override yo'q).
const OTHER_CLASSES = new Set(readdirSync(new URL('static/frontend_v1/css/', root))
  .filter(name => name.endsWith('.css') && name !== 'public-editorial.css')
  .flatMap(name => [...classesIn(stripComments(read(`static/frontend_v1/css/${name}`)))]));

function declarations(css) {
  const out = [];
  for (const block of stripComments(css).matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const selector = block[1].trim();
    for (const declaration of block[2].split(';')) {
      const at = declaration.indexOf(':');
      if (at >= 0) out.push({selector, prop: declaration.slice(0, at).trim(), value: declaration.slice(at + 1).trim()});
    }
  }
  return out;
}

const COLOR_LITERAL = /#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch)\(|\b(?:white|black|red|green|blue|gray|grey|orange|yellow|purple|pink|navy|teal|silver)\b/i;
const LENGTH = /(?<![\w-])(\d*\.?\d+)(px|rem|em|vw|vh|dvh|svh|lvh|ch|ex)\b/g;

test('editorial patternlar faqat tokenlardan: rang, o‘lcham, shrift va burchak literal emas', () => {
  const problems = [];
  for (const {selector, prop, value} of declarations(editorial)) {
    const where = `${selector} { ${prop}: ${value} }`;
    if (prop.startsWith('--')) problems.push(`yangi custom property (tokens.css'ga): ${where}`);
    if (COLOR_LITERAL.test(value)) problems.push(`xom rang: ${where}`);
    if (/!important/.test(value)) problems.push(`!important: ${where}`);
    for (const match of value.matchAll(LENGTH)) {
      if (!(/^(border|outline)/.test(prop) && ['1px', '2px'].includes(match[0]))) problems.push(`literal o‘lcham ${match[0]}: ${where}`);
    }
    if (prop === 'font-size' && !/^var\(--az-text-[a-z0-9]+\)$/.test(value)) problems.push(`font-size token emas: ${where}`);
    if (prop === 'font-weight' && !/^var\(--az-weight-[a-z]+\)$/.test(value)) problems.push(`font-weight token emas: ${where}`);
    if (prop === 'letter-spacing' && !/^var\(--az-tracking[a-z-]*\)$/.test(value)) problems.push(`letter-spacing token emas: ${where}`);
    if (prop === 'line-height' && !/^var\(--az-leading[a-z-]*\)$/.test(value)) problems.push(`line-height token emas: ${where}`);
    if (prop === 'font-family') problems.push(`yangi shrift: ${where}`);
    if (prop === 'border-radius' && !value.split(/\s+/).every(part => /^(var\(--az-radius[a-z-]*\)|0|50%)$/.test(part))) problems.push(`burchak token emas: ${where}`);
    for (const token of value.matchAll(/var\((--[a-z0-9-]+)/g)) {
      if (!TOKENS.has(token[1])) problems.push(`tokens.css'da yo‘q ${token[1]}: ${where}`);
    }
  }
  assert.deepEqual(problems, []);
});

test('editorial faqat production breakpoint’larida va faqat o‘z klasslariga selector yozadi', () => {
  const css = stripComments(editorial);
  const media = [...css.matchAll(/@media\s*([^{]+)\{/g)].map(match => match[1].trim());
  const allowed = new Set(['(width < 1024px)', '(width < 640px)', '(prefers-reduced-motion: reduce)']);
  assert.deepEqual(media.filter(query => !allowed.has(query)), [], 'yangi breakpoint');
  const touched = [...new Set(declarations(css).flatMap(({selector}) => [...selector.matchAll(/\.(-?[a-z_][a-z0-9_-]*)/gi)].map(match => match[1])))];
  assert.ok(touched.length > 20, 'patternlar topilmadi');
  assert.deepEqual(touched.filter(name => OTHER_CLASSES.has(name)), [], 'boshqa V1 komponentini tashqaridan o‘zgartirish');
  assert.deepEqual(touched.filter(name => !/^(p|s)-public-/.test(name)), [], 'yangi klass p-public- yoki s-public- bilan');
});

test('inverse yuza: matn, xira matn va havola to‘q fonda AA (4.5:1) — yorug‘ va qorong‘i', () => {
  const block = selector => Object.fromEntries(declarations(tokensCss)
    .filter(item => item.selector === selector && /^#[0-9a-f]{6}$/i.test(item.value)).map(item => [item.prop, item.value]));
  const luminance = hex => {
    const [r, g, b] = [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16) / 255)
      .map(channel => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const ratio = (a, b) => { const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (high + 0.05) / (low + 0.05); };
  for (const selector of [':root', '[data-theme="dark"]']) {
    const tokens = block(selector);
    for (const foreground of ['--az-on-inverse', '--az-inverse-muted', '--az-inverse-action']) {
      assert.ok(tokens[foreground] && tokens['--az-inverse'], `${selector}: ${foreground} yoki --az-inverse yo‘q`);
      const value = ratio(tokens[foreground], tokens['--az-inverse']);
      assert.ok(value >= 4.5, `${selector} ${foreground} / --az-inverse = ${value.toFixed(2)} < 4.5`);
    }
  }
  // Yuza faqat tokenlarni almashtiradi: komponent selectori ham, xom rang ham yo‘q.
  for (const {prop, value} of declarations(tokensCss).filter(item => item.selector === '[data-surface="inverse"]')) {
    assert.match(value, /^var\(--az-[a-z0-9-]+\)$/, `[data-surface="inverse"] { ${prop}: ${value} }`);
    assert.ok(prop.startsWith('--az-') || ['background', 'color'].includes(prop), `[data-surface="inverse"] ${prop}`);
  }
});

test('burchaklar owner sozlamasiga ergashadi: karta burchagi va keyin qo‘shilgan "Urg‘u burchagi"', () => {
  const catalog = JSON.parse(read('core/design_catalog.json'));
  const field = catalog.groups.flatMap(group => group.fields).find(item => item.css === '--dc-shape-radius');
  assert.ok(field, '--dc-shape-radius katalogda yo‘q');
  assert.equal(field.default, null, 'standart bo‘sh — karta burchagidan meros');
  assert.ok(field.added, 'keyin qo‘shilgan maydon `added` belgisiz — eski nashrlar o‘qilmay qoladi');
  const runtime = stripComments(read('static/backoffice/design-runtime.css'));
  assert.match(runtime, /--az-radius-tile:\s*var\(--dc-card-radius,\s*var\(--az-radius\)\)/);
  assert.match(runtime, /--az-radius-shape:\s*var\(--dc-shape-radius,\s*calc\(var\(--dc-card-radius,\s*var\(--az-radius-lg\)\)\s*\*\s*2\)\)/);
  assert.ok(TOKENS.has('--az-radius-tile') && TOKENS.has('--az-radius-shape'), 'sozlamasiz qiymat tokens.css’da');
});
