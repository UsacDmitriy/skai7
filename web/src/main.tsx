import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

// Порядок важен: токены/шрифт (d1) → Tailwind (f1) → переопределения base.
import './styles/tokens.css'
import './index.css'

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('Не найден #root для монтирования приложения')

createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
