import axios from 'axios';

const API = axios.create({ baseURL: 'http://localhost:8000' });

export const sendChat = (message) =>
  API.post('/chat', { session_id: 'demo', message });

export const getInteraction = () =>
  API.get('/interaction');

export const saveInteraction = () =>
  API.post('/save-interaction');

export const resetInteraction = () =>
  API.post('/reset');
