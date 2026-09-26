// Browser-independent draft rules. No timers, network, grading or autosave.
export function valueOf(value = {}) {
  return {choice_id: String(value.choice_id || ''), option_ids: [...(value.option_ids || [])].map(String).sort(),
    answer_text: value.answer_text || '', flagged: Boolean(value.flagged), audio_url: value.audio_url || ''};
}
export const same = (a, b) => JSON.stringify(valueOf(a)) === JSON.stringify(valueOf(b));
export const dirty = row => !same(row.base, row.draft) || Boolean(row.file || row.audioLost || row.recording);
export const blocked = (rows, pending, busy, closed) => Boolean(pending || busy || closed || Object.values(rows).some(row => dirty(row) || row.stale));
export function makeRow(saved, restored) {
  const row = {base: {...valueOf(saved), version: saved.version}, draft: valueOf(saved), stale: false, file: false, audioLost: false};
  if (restored?.base && restored?.draft) {
    row.base = restored.base;
    row.draft = valueOf(restored.draft);
    row.audioLost = Boolean(restored.audioLost);
    row.stale = saved.version !== row.base.version;
  }
  row.server = saved;
  return row;
}
export function receive(row, saved, acknowledged = false) {
  row.server = saved;
  if (acknowledged || !dirty(row)) {
    row.base = {...valueOf(saved), version: saved.version};
    row.draft = valueOf(saved);
    row.file = false;
    row.audioLost = false;
    row.stale = false;
  } else row.stale = saved.version !== row.base.version;
}
export function rebase(row) {
  row.base = {...valueOf(row.server), version: row.server.version};
  row.draft.audio_url = row.server.audio_url;
  row.stale = false;
}
export const answered = value => Boolean(value.choice_id || value.option_ids?.length || value.answer_text?.trim() || value.audio_url);
export function packDraft(row) {
  return {base: {...valueOf(row.base), version: row.base.version}, draft: valueOf(row.draft),
    audioLost: Boolean(row.file || row.audioLost || row.recording)};
}
export function acknowledgedKey(pending, receipt, state) {
  if (!pending || receipt?.id !== pending.operation_id || receipt.command !== 'save' || receipt.attempt_id !== state.attempt_id) return null;
  return state.answers[pending.key]?.version === pending.version + 1 ? pending.key : null;
}
export function clockLabel(seconds) {
  if (seconds === null) return 'Vaqt cheklanmagan';
  return `Serverda qolgan: ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}
