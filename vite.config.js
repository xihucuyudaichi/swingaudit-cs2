import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],base:'./',server:{port:5177,strictPort:true,proxy:{'/api':'http://127.0.0.1:5188'}},preview:{port:5177,strictPort:true,proxy:{'/api':'http://127.0.0.1:5188'}}});
