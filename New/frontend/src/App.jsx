import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertTriangle, Radio } from 'lucide-react'
import { calculateRoute, getBootstrap } from './api'
import voyageAudio from './assets/voyage-ocean.mp3'
import MapView from './MapView'
import Results from './Results'
import ThemeToggle from './ThemeToggle'
import VoyagePlanner from './VoyagePlanner'

const localDate = () => {
  const date = new Date(Date.now() + 3600000)
  return new Date(date - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

const initial = {
  departure_time: localDate(),
  vessel: { ship_type: 'container', fuel_onboard_t: 2500, fuel_capacity_t: 3200, fuel_reserve_percent: 15, displacement_ex_fuel_t: 38000, reference_displacement_t: 40000, actual_draft_m: 10.5, design_draft_m: 12, service_speed_kn: 16, engine_mcr_kw: 12000, normal_engine_load_percent: 75, sfoc_g_kwh: 175, propulsion_efficiency_percent: 70, max_wave_height_m: 6, max_wind_speed_ms: 25 },
  priorities: { fuel: 50, time: 30, safety: 20 },
  use_weather: true, use_alert_zones: true, alert_avoidance: .8, prefer_alternate_route: true,
}

export default function App() {
  const [ports, setPorts] = useState([])
  const [config, setConfig] = useState({ alerts: [] })
  const [stops, setStops] = useState(['INBOM', 'LKCMB', 'SGSIN'])
  const [form, setForm] = useState(initial)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showAlerts, setShowAlerts] = useState(true)
  const [theme, setTheme] = useState(() => localStorage.getItem('samudra-theme') || 'light')
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [audioBlocked, setAudioBlocked] = useState(false)
  const audioRef = useRef(null)

  const playVoyageAudio = useCallback((volume = 0.18) => {
    const audio = audioRef.current
    if (!audio) return
    audio.volume = volume
    const playback = audio.play()
    if (playback) {
      playback.then(() => setAudioBlocked(false)).catch(() => setAudioBlocked(true))
    }
  }, [])

  useEffect(() => {
    document.body.classList.toggle('theme-dark', theme === 'dark')
    localStorage.setItem('samudra-theme', theme)
  }, [theme])

  useEffect(() => {
    getBootstrap().then(({ ports: loadedPorts, ...loadedConfig }) => {
      setPorts(loadedPorts); setConfig(loadedConfig)
    }).catch(requestError => setError(requestError.message))
  }, [])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    if (result && soundEnabled && !document.hidden) {
      playVoyageAudio()
    } else if (!loading) {
      audio.pause()
      if (!result) audio.currentTime = 0
    }
  }, [loading, playVoyageAudio, result, soundEnabled])

  useEffect(() => {
    const handleVisibility = () => {
      const audio = audioRef.current
      if (!audio) return
      if (document.hidden) audio.pause()
      else if (result && soundEnabled) playVoyageAudio()
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [playVoyageAudio, result, soundEnabled])

  const toggleVoyageSound = () => {
    const audio = audioRef.current
    if (soundEnabled && audioBlocked && result) {
      playVoyageAudio()
      return
    }
    const nextEnabled = !soundEnabled
    setSoundEnabled(nextEnabled)
    setAudioBlocked(false)
    if (nextEnabled && result) playVoyageAudio()
    else audio?.pause()
  }

  const submit = async event => {
    event.preventDefault(); setLoading(true); setResult(null); setError('')
    if (soundEnabled && audioRef.current) {
      audioRef.current.currentTime = 0
      playVoyageAudio(0.001)
    }
    try {
      setResult(await calculateRoute({ ...form, departure_time: new Date(form.departure_time).toISOString(), ports: stops }))
    } catch (requestError) { setError(requestError.message) }
    finally { setLoading(false) }
  }

  return <div className="app">
    <VoyagePlanner ports={ports} stops={stops} setStops={setStops} form={form} setForm={setForm} shipProfiles={config.shipProfiles || []} onSubmit={submit} loading={loading} />
    <div className="command">
      <header><div><Radio /> LIVE PLANNING ENVIRONMENT <span>{config.weatherProvider || 'Date-indexed fallback'}</span></div><p>INDIAN OCEAN · {new Date().toUTCString().slice(5, 22)} UTC</p></header>
      <ThemeToggle theme={theme} onChange={setTheme} />
      <MapView apiKey={config.googleMapsApiKey} alerts={config.alerts || []} ports={ports} stops={stops} result={result} departureTime={form.departure_time} weatherEnabled={form.use_weather} showAlerts={showAlerts} setShowAlerts={setShowAlerts} soundEnabled={soundEnabled} audioBlocked={audioBlocked} onToggleSound={toggleVoyageSound} />
      {loading && <div className="loading"><div className="radar" /><b>Optimizing fuel and voyage path…</b><span>Evaluating water corridors, vessel state and forecast conditions</span></div>}
      {error && <div className="error"><AlertTriangle /><span><b>Unable to calculate voyage</b>{error}</span><button onClick={() => setError('')}>×</button></div>}
      <Results result={result} onClose={() => setResult(null)} />
      <audio ref={audioRef} src={voyageAudio} loop preload="metadata" aria-hidden="true" />
    </div>
  </div>
}
