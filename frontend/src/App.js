import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { setInteractionData } from './store';
import { getInteraction } from './api';
import InteractionForm from './components/InteractionForm';
import ChatPanel from './components/ChatPanel';
import Header from './components/Header';
import './App.css';

export default function App() {
  const dispatch = useDispatch();

  useEffect(() => {
    getInteraction()
      .then(res => dispatch(setInteractionData(res.data)))
      .catch(() => {});
  }, [dispatch]);

  return (
    <div className="app-root">
      <Header />
      <div className="split-screen">
        <div className="panel left-panel">
          <InteractionForm />
        </div>
        <div className="panel-divider" />
        <div className="panel right-panel">
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
