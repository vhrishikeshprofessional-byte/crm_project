import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { addChatMessage, setInteractionData, setLoading, setError } from '../store';
import { sendChat } from '../api';
import './ChatPanel.css';

const SUGGESTED_PROMPTS = [
  "Met Dr. Sharma today, discussed Product X efficacy, positive sentiment",
  "Call with Dr. Patel, shared brochure, follow-up in 2 weeks",
  "Change sentiment to negative",
  "Suggest follow-up actions",
  "Is my data complete and ready to save?"
];

export default function ChatPanel() {
  const dispatch = useDispatch();
  const { chatMessages, loading } = useSelector(s => s.interaction);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, typing]);

  const handleSend = async (msg) => {
    const text = (msg || input).trim();
    if (!text) return;

    dispatch(addChatMessage({ role: 'user', content: text, time: now() }));
    setInput('');
    setTyping(true);
    dispatch(setError(null));

    try {
      const res = await sendChat(text);
      const { reply, interaction_data } = res.data;
      dispatch(setInteractionData(interaction_data));
      dispatch(addChatMessage({ role: 'ai', content: reply, time: now() }));
    } catch (err) {
      dispatch(addChatMessage({
        role: 'ai',
        content: '⚠️ Connection error. Please ensure the backend is running on port 8000.',
        time: now(),
        isError: true
      }));
    } finally {
      setTyping(false);
      inputRef.current?.focus();
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-root">
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="ai-avatar">
            <span>✦</span>
          </div>
          <div>
            <div className="chat-title">AI Assistant</div>
            <div className="chat-subtitle">Log interaction via chat</div>
          </div>
        </div>
        <div className="model-badge">gemma2-9b-it</div>
      </div>

      <div className="chat-body">
        {chatMessages.length === 0 && (
          <div className="chat-empty">
            <div className="empty-icon">✦</div>
            <p className="empty-title">Start by describing your HCP interaction</p>
            <p className="empty-sub">
              Speak naturally — I'll extract the structured data automatically.
            </p>
            <div className="prompt-chips">
              {SUGGESTED_PROMPTS.map((p, i) => (
                <button key={i} className="chip" onClick={() => handleSend(p)}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {chatMessages.map((msg, i) => (
          <div key={i} className={`message-row ${msg.role}`}>
            {msg.role === 'ai' && (
              <div className="msg-avatar ai-msg-avatar">✦</div>
            )}
            <div className={`bubble ${msg.role} ${msg.isError ? 'error-bubble' : ''}`}>
              <div className="bubble-content">{formatMessage(msg.content)}</div>
              <div className="bubble-time">{msg.time}</div>
            </div>
            {msg.role === 'user' && (
              <div className="msg-avatar user-msg-avatar">U</div>
            )}
          </div>
        ))}

        {typing && (
          <div className="message-row ai">
            <div className="msg-avatar ai-msg-avatar">✦</div>
            <div className="bubble ai typing-bubble">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="chat-footer">
        <div className="input-row">
          <textarea
            ref={inputRef}
            className="chat-input"
            rows={2}
            placeholder='Describe interaction... (e.g. "Met Dr. Smith, discussed efficacy, positive")'
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={typing}
          />
          <button
            className="send-btn"
            onClick={() => handleSend()}
            disabled={!input.trim() || typing}
          >
            {typing ? <span className="spinner-sm" /> : '↑'}
          </button>
        </div>
        <div className="footer-hint">
          Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line
        </div>
      </div>
    </div>
  );
}

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatMessage(text) {
  // Bold **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i}>{p.slice(2, -2)}</strong>;
    }
    // Handle bullet points
    if (p.includes('\n•') || p.includes('\n-')) {
      return <span key={i}>{p.split('\n').map((line, j) => (
        <span key={j}>{line}<br /></span>
      ))}</span>;
    }
    return <span key={i}>{p}</span>;
  });
}
