import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const code = readFileSync(new URL('../../static/frontend_v1/js/auth-validation.js', import.meta.url), 'utf8');

function api() {
  const sandbox = {};
  sandbox.globalThis = sandbox;
  runInNewContext(code, sandbox);  // `document` yo'q: faqat sof funksiyalar e'lon qilinadi
  return sandbox.AzAuthValidation;
}

const field = (name, value, validity = {valid: true}, extra = {}) => ({name, value, validity, type: 'text', ...extra});

test('script loads without a DOM and exposes only pure helpers', () => {
  const v = api();
  assert.equal(typeof v.validate, 'function');
  assert.equal(v.summaryText(3), '3 ta maydonni tekshiring.');
});

test('native validity maps to one Uzbek message per field', () => {
  const v = api();
  assert.equal(v.messageFor(field('a', '', {valid: false, valueMissing: true})), 'Bu maydonni to‘ldiring.');
  assert.equal(v.messageFor(field('e', 'x', {valid: false, typeMismatch: true}, {type: 'email'})), 'Email manzilini to‘g‘ri kiriting, masalan: ism@misol.uz.');
  assert.equal(v.messageFor(field('n', 'x'.repeat(40), {valid: false, tooLong: true}, {maxLength: 30})), 'Ko‘pi bilan 30 belgi kiriting.');
  assert.equal(v.messageFor(field('ok', 'x')), '');
});

test('required, email and password mismatch are reported together in DOM order', () => {
  const v = api();
  const fields = [
    field('first_name', '', {valid: false, valueMissing: true}),
    field('email', 'bad', {valid: false, typeMismatch: true}, {type: 'email'}),
    field('password1', 'Bir-Parol-1'),
    field('password2', 'Boshqa-Parol-2'),
  ];
  const problems = v.validate(fields);
  assert.deepEqual(problems.map(p => p.field.name), ['first_name', 'email', 'password2']);
  assert.equal(problems[2].message, 'Ikkala parol bir xil emas — ikkalasini ham tekshiring.');
});

test('mismatch is not reported while either password is empty, and reset confirm pairs too', () => {
  const v = api();
  assert.deepEqual(v.validate([field('password1', 'abc'), field('password2', '')]), []);
  const problems = v.validate([field('new_password1', 'Yangi-1'), field('new_password2', 'Yangi-2')]);
  assert.deepEqual(problems.map(p => p.field.name), ['new_password2']);
});

test('no password strength policy is invented on the client', () => {
  const v = api();
  // Qisqa yoki oddiy parol — server qoidasi; mijoz uni rad etmaydi.
  assert.deepEqual(v.validate([field('password1', '1'), field('password2', '1')]), []);
  assert.ok(!/kuchli|zaif|strength/i.test(code));
});
