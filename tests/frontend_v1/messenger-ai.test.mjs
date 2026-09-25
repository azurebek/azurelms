import test from 'node:test';
import assert from 'node:assert/strict';
import {mergeRun, retryAllowed} from '../../static/frontend_v1/js/messenger-ai.mjs';

test('AI retry only follows a canonical terminal state', () => {
  for (const status of ['unknown', 'pending', 'running', undefined]) assert.equal(retryAllowed({status}), false);
  for (const status of ['failed', 'fallback', 'succeeded']) assert.equal(retryAllowed({status}), true);
  assert.equal(retryAllowed(null), false);
});
test('older status/history cannot unlock a newer retry', () => {
  const pending = {status: 'unknown', user_message_id: 8, awaiting_after: 12};
  assert.deepEqual(mergeRun(pending, {status: 'succeeded', user_message_id: 8, run_id: 12}), pending);
  assert.equal(mergeRun(pending, {status: 'running', user_message_id: 8, run_id: 13}).status, 'running');
});
test('stale history and out-of-order status do not revive completed work', () => {
  const completed = {status: 'failed', user_message_id: 8, run_id: 12};
  assert.deepEqual(mergeRun(completed, {status: 'running', user_message_id: 8, run_id: 11}), completed);
  assert.deepEqual(mergeRun(completed, {status: 'running', user_message_id: 8, run_id: 12}), completed);
  assert.equal(mergeRun(completed, {status: 'running', user_message_id: 8, run_id: 13}).status, 'running');
});
