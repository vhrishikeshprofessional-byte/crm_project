import { configureStore, createSlice } from '@reduxjs/toolkit';

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    interactionData: {},
    loading: false,
    error: null,
    chatMessages: [],
    saveSuccess: false,
  },
  reducers: {
    setLoading: (state, action) => { state.loading = action.payload; },
    setError: (state, action) => { state.error = action.payload; },
    setInteractionData: (state, action) => { state.interactionData = action.payload; },
    updateField: (state, action) => {
      const { field, value } = action.payload;
      state.interactionData[field] = value;
    },
    addChatMessage: (state, action) => {
      state.chatMessages.push(action.payload);
    },
    clearChatMessages: (state) => { state.chatMessages = []; },
    setSaveSuccess: (state, action) => { state.saveSuccess = action.payload; },
    resetAll: (state) => {
      state.interactionData = {};
      state.chatMessages = [];
      state.error = null;
      state.saveSuccess = false;
    }
  }
});

export const {
  setLoading, setError, setInteractionData,
  updateField, addChatMessage, clearChatMessages,
  setSaveSuccess, resetAll
} = interactionSlice.actions;

export const store = configureStore({
  reducer: { interaction: interactionSlice.reducer }
});
