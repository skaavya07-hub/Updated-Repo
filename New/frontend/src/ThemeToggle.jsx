import { Moon, Sun } from 'lucide-react'

export default function ThemeToggle({ theme, onChange }) {
  return (
    <div className="themeToggle" role="group" aria-label="Color theme">
      <button type="button" className={theme === 'light' ? 'active' : ''} onClick={() => onChange('light')} aria-pressed={theme === 'light'}>
        <Sun /> <span>Light</span>
      </button>
      <button type="button" className={theme === 'dark' ? 'active' : ''} onClick={() => onChange('dark')} aria-pressed={theme === 'dark'}>
        <Moon /> <span>Dark</span>
      </button>
    </div>
  )
}
