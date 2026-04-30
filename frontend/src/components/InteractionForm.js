import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateField, setLoading, setError, setSaveSuccess, resetAll } from '../store';
import { saveInteraction, resetInteraction } from '../api';
import './InteractionForm.css';

const INTERACTION_TYPES = ['Meeting', 'Call', 'Visit'];
const SENTIMENTS = ['Positive', 'Neutral', 'Negative'];

export default function InteractionForm() {
  const dispatch = useDispatch();
  const { interactionData, loading, saveSuccess, error } = useSelector(s => s.interaction);
  const [saving, setSaving] = useState(false);

  const d = interactionData || {};

  const normalizeValue = (value) => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string' && ['null', 'undefined'].includes(value.trim().toLowerCase())) return '';
    return value;
  };

  const handleChange = (field, value) => {
    dispatch(updateField({ field, value }));
  };

  const handleArrayChange = (field, value) => {
    const arr = value.split(',').map(s => s.trim()).filter(Boolean);
    dispatch(updateField({ field, value: arr }));
  };

  const handleSave = async () => {
    setSaving(true);
    dispatch(setError(null));
    try {
      await saveInteraction();
      dispatch(setSaveSuccess(true));
      dispatch(resetAll());
      setTimeout(() => dispatch(setSaveSuccess(false)), 3000);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to save interaction.';
      dispatch(setError(msg));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    await resetInteraction();
    dispatch(resetAll());
  };

  const followUps = Array.isArray(d.follow_ups) ? d.follow_ups : [];
  const attendees = Array.isArray(d.attendees) ? d.attendees.join(', ') : normalizeValue(d.attendees);
  const materials = Array.isArray(d.materials_shared) ? d.materials_shared.join(', ') : normalizeValue(d.materials_shared);
  const samples = Array.isArray(d.samples_distributed) ? d.samples_distributed.join(', ') : normalizeValue(d.samples_distributed);

  return (
    <div className="form-root">
      <div className="form-header">
        <h2 className="form-title">Interaction Details</h2>
        <div className="form-actions-top">
          <button className="btn-ghost" onClick={handleReset}>Reset</button>
          <button
            className="btn-primary save-btn"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? <><span className="spinner" /> Saving…</> : '💾 Save Interaction'}
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div className="alert success">✅ Interaction saved to database successfully!</div>
      )}
      {error && (
        <div className="alert error">⚠️ {error}</div>
      )}

      <div className="form-body">
        {/* Row 1 */}
        <div className="form-row two-col">
          <div className="field-group">
            <label className="field-label">HCP Name</label>
            <input
              className="field-input"
              placeholder="Search or select HCP..."
              value={d.hcp_name || ''}
              onChange={e => handleChange('hcp_name', e.target.value)}
            />
          </div>
          <div className="field-group">
            <label className="field-label">Interaction Type</label>
            <select
              className="field-input field-select"
              value={d.interaction_type || ''}
              onChange={e => handleChange('interaction_type', e.target.value)}
            >
              <option value="">Select type...</option>
              {INTERACTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>

        {/* Row 2 */}
        <div className="form-row two-col">
          <div className="field-group">
            <label className="field-label">Date</label>
            <input
              type="date"
              className="field-input"
              value={normalizeValue(d.date)}
              onChange={e => handleChange('date', e.target.value)}
            />
          </div>
          <div className="field-group">
            <label className="field-label">Time</label>
            <input
              type="time"
              className="field-input"
              value={normalizeValue(d.time)}
              onChange={e => handleChange('time', e.target.value)}
            />
          </div>
        </div>

        {/* Attendees */}
        <div className="field-group">
          <label className="field-label">Attendees <span className="field-hint">(comma-separated)</span></label>
          <input
            className="field-input"
            placeholder="Enter names or search..."
            value={attendees}
            onChange={e => handleArrayChange('attendees', e.target.value)}
          />
        </div>

        {/* Topics */}
        <div className="field-group">
          <label className="field-label">Topics Discussed</label>
          <textarea
            className="field-input field-textarea"
            placeholder="Enter key discussion points..."
            value={normalizeValue(d.topics_discussed)}
            onChange={e => handleChange('topics_discussed', e.target.value)}
            rows={3}
          />
        </div>

        {/* Materials & Samples */}
        <div className="form-row two-col">
          <div className="field-group">
            <label className="field-label">Materials Shared <span className="field-hint">(comma-separated)</span></label>
            <input
              className="field-input"
              placeholder="e.g. Brochure, PDF..."
              value={materials}
              onChange={e => handleArrayChange('materials_shared', e.target.value)}
            />
            {Array.isArray(d.materials_shared) && d.materials_shared.length > 0 && (
              <div className="tag-list">
                {d.materials_shared.map((m, i) => <span key={i} className="tag">{m}</span>)}
              </div>
            )}
          </div>
          <div className="field-group">
            <label className="field-label">Samples Distributed <span className="field-hint">(comma-separated)</span></label>
            <input
              className="field-input"
              placeholder="e.g. Drug A, Drug B..."
              value={samples}
              onChange={e => handleArrayChange('samples_distributed', e.target.value)}
            />
            {Array.isArray(d.samples_distributed) && d.samples_distributed.length > 0 && (
              <div className="tag-list">
                {d.samples_distributed.map((s, i) => <span key={i} className="tag tag-sample">{s}</span>)}
              </div>
            )}
          </div>
        </div>

        {/* Sentiment */}
        <div className="field-group">
          <label className="field-label">Observed / Inferred HCP Sentiment</label>
          <div className="sentiment-group">
            {SENTIMENTS.map(s => (
              <label key={s} className={`sentiment-option ${d.sentiment === s ? 'active-' + s.toLowerCase() : ''}`}>
                <input
                  type="radio"
                  name="sentiment"
                  value={s}
                  checked={d.sentiment === s}
                  onChange={() => handleChange('sentiment', s)}
                />
                <span className={`sentiment-emoji ${s.toLowerCase()}`}>
                  {s === 'Positive' ? '😊' : s === 'Neutral' ? '😐' : '😟'}
                </span>
                {s}
              </label>
            ))}
          </div>
        </div>

        {/* Outcomes */}
        <div className="field-group">
          <label className="field-label">Outcomes</label>
          <textarea
            className="field-input field-textarea"
            placeholder="Key outcomes or agreements..."
            value={normalizeValue(d.outcomes)}
            onChange={e => handleChange('outcomes', e.target.value)}
            rows={2}
          />
        </div>

        {/* Follow-ups */}
        <div className="field-group">
          <label className="field-label">Follow-up Actions</label>
          <textarea
            className="field-input field-textarea"
            placeholder="Enter next steps or tasks..."
            value={Array.isArray(d.follow_ups) ? d.follow_ups.join('\n') : (d.follow_ups || '')}
            onChange={e => {
              const arr = e.target.value.split('\n').map(s => s.trim()).filter(Boolean);
              handleChange('follow_ups', arr);
            }}
            rows={2}
          />
          {followUps.length > 0 && (
            <div className="ai-followups">
              <span className="ai-label">✨ AI Suggested Follow-ups:</span>
              <ul>
                {followUps.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
