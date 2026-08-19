import {
  Anchor,
  ArrowDown,
  ArrowUp,
  CalendarClock,
  Fuel,
  Gauge,
  Plus,
  Route,
  Shield,
  Ship,
  Trash2,
  Waves,
  Wind,
} from 'lucide-react'
import brandLogo from './assets/samudra-route-logo.png'

const vesselFields = [
  ['fuel_onboard_t', 'Fuel onboard', 't', Fuel],
  ['fuel_capacity_t', 'Tank capacity', 't', Fuel],
  ['fuel_reserve_percent', 'Fuel reserve', '%', Shield],
  ['displacement_ex_fuel_t', 'Displacement ex fuel', 't', Anchor],
  ['reference_displacement_t', 'Reference displacement', 't', Anchor],
  ['actual_draft_m', 'Actual draft', 'm', Waves],
  ['design_draft_m', 'Design draft', 'm', Waves],
  ['service_speed_kn', 'Service speed', 'kn', Gauge],
  ['engine_mcr_kw', 'Engine MCR', 'kW', Gauge],
  ['normal_engine_load_percent', 'Normal engine load', '%', Gauge],
  ['sfoc_g_kwh', 'SFOC', 'g/kWh', Fuel],
  ['propulsion_efficiency_percent', 'Propulsion efficiency', '%', Gauge],
  ['max_wave_height_m', 'Maximum wave', 'm', Waves],
  ['max_wind_speed_ms', 'Maximum wind', 'm/s', Wind],
]

export default function VoyagePlanner({
  ports,
  stops,
  setStops,
  form,
  setForm,
  shipProfiles,
  onSubmit,
  loading,
}) {
  const set = (group, key, value) => setForm(current => ({
    ...current,
    [group]: { ...current[group], [key]: Number(value) },
  }))
  const move = (index, direction) => {
    const nextStops = [...stops]
    ;[nextStops[index], nextStops[index + direction]] = [nextStops[index + direction], nextStops[index]]
    setStops(nextStops)
  }
  const availableShipProfiles = shipProfiles.length
    ? shipProfiles
    : [{ key: 'container', label: 'Container ship', description: 'Schedule-aware routing with balanced fuel and safety exposure.' }]
  const activeShipProfile = availableShipProfiles.find(profile => profile.key === form.vessel.ship_type)
    || availableShipProfiles[0]
  const setShipType = value => setForm(current => ({
    ...current,
    vessel: { ...current.vessel, ship_type: value },
  }))

  return <aside className="planner">
    <div className="brand">
      <div className="brandMark"><img src={brandLogo} alt="Samudra Route logo" /></div>
      <div className="brandText">
        <small className="brandEyebrow">VOYAGE PLANNER</small>
        <b className="brandName">ֆᵃᵐᵘᵈʳᵃ Ꮢᵒᵘᵗᵉ</b>
        <span className="brandTagline">Maritime intelligence for safer, smarter voyages</span>
      </div>
    </div>
    <form onSubmit={onSubmit}>
      <section>
        <h2><Anchor /> Voyage plan</h2>
        <p className="hint">Build a continuous 2–8 port passage</p>
        <div className="stops">
          {stops.map((code, index) => <div className="stop" key={index}>
            <span className="stopNo">{index + 1}</span>
            <label>
              <small>{index === 0 ? 'DEPARTURE' : index === stops.length - 1 ? 'FINAL DESTINATION' : `WAYPOINT ${index}`}</small>
              <select value={code} onChange={event => {
                const nextStops = [...stops]
                nextStops[index] = event.target.value
                setStops(nextStops)
              }}>
                {ports.map(port => <option value={port.code} key={port.code}>{port.name} · {port.country}</option>)}
              </select>
            </label>
            <div className="stopActions">
              {index > 0 && <button type="button" onClick={() => move(index, -1)} aria-label="Move up"><ArrowUp /></button>}
              {index < stops.length - 1 && <button type="button" onClick={() => move(index, 1)} aria-label="Move down"><ArrowDown /></button>}
              {index > 0 && index < stops.length - 1 && <button type="button" onClick={() => setStops(stops.filter((_, stopIndex) => stopIndex !== index))} aria-label="Remove"><Trash2 /></button>}
            </div>
          </div>)}
        </div>
        {stops.length < 8 && ports.length > 0 && <button className="add" type="button" onClick={() => setStops([
          ...stops,
          ports.find(port => !stops.includes(port.code))?.code || ports[0].code,
        ])}><Plus /> Add intermediate port</button>}
        <label className="full">
          <small><CalendarClock /> DEPARTURE (LOCAL INPUT)</small>
          <input type="datetime-local" value={form.departure_time} onChange={event => setForm({ ...form, departure_time: event.target.value })} />
        </label>
      </section>
      <section>
        <h2><Gauge /> Vessel profile</h2>
        <label className="shipTypeField">
          <small><Ship /> VESSEL TYPE</small>
          <select value={form.vessel.ship_type} onChange={event => setShipType(event.target.value)}>
            {availableShipProfiles.map(profile => <option value={profile.key} key={profile.key}>{profile.label}</option>)}
          </select>
          <em>{activeShipProfile.description}</em>
        </label>
        <div className="fieldGrid">
          {vesselFields.map(([key, label, unit, Icon]) => <label key={key}>
            <small><Icon />{label}</small>
            <div><input type="number" step="any" value={form.vessel[key]} onChange={event => set('vessel', key, event.target.value)} /><span>{unit}</span></div>
          </label>)}
        </div>
      </section>
      <section>
        <h2><Shield /> Optimization priorities</h2>
        {[['fuel', 'Minimum fuel'], ['time', 'Shortest time'], ['safety', 'Maximum safety']].map(([key, label]) => <label className="range" key={key}>
          <span>{label}<b>{form.priorities[key]}%</b></span>
          <input type="range" min="0" max="100" value={form.priorities[key]} onChange={event => set('priorities', key, event.target.value)} />
        </label>)}
        <div className="toggleRow">
          <label><input type="checkbox" checked={form.use_weather} onChange={event => setForm({ ...form, use_weather: event.target.checked })} /><span />Weather routing</label>
          <label><input type="checkbox" checked={form.use_alert_zones} onChange={event => setForm({ ...form, use_alert_zones: event.target.checked })} /><span />Alert avoidance</label>
        </div>
        <label className="range">
          <span>Avoidance strength<b>{Math.round(form.alert_avoidance * 100)}%</b></span>
          <input type="range" min="0" max="1" step=".05" value={form.alert_avoidance} onChange={event => setForm({ ...form, alert_avoidance: Number(event.target.value) })} />
        </label>
      </section>
      <button className="calculate" disabled={loading}><Route />{loading ? 'Optimizing fuel and voyage path…' : 'Optimize voyage'}</button>
    </form>
    <footer>Decision-support prototype · Not certified navigation software</footer>
  </aside>
}
