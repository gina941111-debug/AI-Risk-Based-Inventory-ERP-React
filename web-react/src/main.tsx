import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import 'antd/dist/reset.css'
import './styles.css'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider theme={{ token: { colorPrimary: '#3b82f6', borderRadius: 12, fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif' } }}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
