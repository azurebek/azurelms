/* Transport-independent draft/delivery rules. No fabricated receipts or retry. */
export const prefix = 'azurelms:v1:messenger:';
export function draftKey(scope, room) { return `${prefix}${scope}:${room}`; }
export function parseDraft(raw) {
  try {
    const value = JSON.parse(raw);
    return {text: typeof value?.text === 'string' ? value.text : '', pending: value?.pending || null,
      edits: value?.edits && typeof value.edits === 'object' ? value.edits : {}};
  } catch { return {text: '', pending: null, edits: {}}; }
}
export function canSend({connected, loaded, blocked, pending, text, file}) {
  return !!(connected && loaded && !blocked && !pending && (text.trim() || file));
}
export function confirms(pending, event, user, room) {
  return !!(pending?.id && event.client_message_id === pending.id &&
    String(event.sender_id) === String(user) && String(event.room_id) === String(room) && event.message_id);
}
export function mergeMessages(current, incoming) {
  const map = new Map(current.map(m => [Number(m.id || m.message_id), m]));
  for (const message of incoming) {
    const id = Number(message.id || message.message_id);
    if (Number.isSafeInteger(id) && id > 0) map.set(id, message);
  }
  return [...map.values()].sort((a, b) => Number(a.id || a.message_id) - Number(b.id || b.message_id));
}
export function composeShortcut(event) {
  return !!(event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.isComposing);
}
