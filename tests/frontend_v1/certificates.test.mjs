import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

test('certificate print only follows a user click, never initial load', () => {
  let calls = 0;
  const button = {addEventListener(name, fn) {assert.equal(name, 'click'); this.click = fn;}};
  runInNewContext(readFileSync(new URL('../../static/frontend_v1/js/certificates.js', import.meta.url), 'utf8'), {
    document: {querySelectorAll: () => [button]}, window: {print() {calls++;}},
  });
  assert.equal(calls, 0);
  button.click(); assert.equal(calls, 1);
});
