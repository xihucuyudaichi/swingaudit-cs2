import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import '@fontsource-variable/manrope';
import ConnectedApp from './ConnectedApp';

createRoot(document.getElementById('root')).render(<ConnectedApp />);
