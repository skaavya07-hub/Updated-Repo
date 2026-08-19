import { useEffect, useRef, useState } from 'react'
import { CloudSun, Layers, Map as MapIcon, ShieldAlert, Ship, Volume2, VolumeX } from 'lucide-react'
import { getEnvironment } from './api'

const zoneColor = { conflict: '#ef4444', piracy: '#f97316', restricted: '#eab308', weather: '#f59e0b' }

const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#039;',
})[character])

const weatherColor = conditions => {
  const severity = Math.max(conditions.wave_m / 6, conditions.wind_ms / 25)
  if (severity >= 0.8) return '#ef4444'
  if (severity >= 0.5) return '#f59e0b'
  return '#0891b2'
}

const segmentDistance = (a, b) => {
  const toRadians = value => value * Math.PI / 180
  const latitudeDelta = toRadians(b.lat - a.lat)
  const longitudeDelta = toRadians((((b.lng - a.lng) + 540) % 360) - 180)
  const latitudeA = toRadians(a.lat)
  const latitudeB = toRadians(b.lat)
  const haversine = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(latitudeA) * Math.cos(latitudeB) * Math.sin(longitudeDelta / 2) ** 2
  const boundedHaversine = Math.min(1, Math.max(0, haversine))
  return 3440.065 * 2 * Math.atan2(Math.sqrt(boundedHaversine), Math.sqrt(1 - boundedHaversine))
}

const segmentBearing = (a, b) => {
  const toRadians = value => value * Math.PI / 180
  const latitudeA = toRadians(a.lat)
  const latitudeB = toRadians(b.lat)
  const longitudeDelta = toRadians((((b.lng - a.lng) + 540) % 360) - 180)
  const y = Math.sin(longitudeDelta) * Math.cos(latitudeB)
  const x = Math.cos(latitudeA) * Math.sin(latitudeB)
    - Math.sin(latitudeA) * Math.cos(latitudeB) * Math.cos(longitudeDelta)
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360
}

const SHIP_SYMBOL_PATH = 'M 0 -17 L 8 -5 L 7 9 L 3 14 L 0 17 L -3 14 L -7 9 L -8 -5 Z'

const forecastLocations = (alerts, ports, stops, result) => {
  const weatherZones = alerts
    .filter(zone => zone.type === 'weather')
    .map(zone => ({
      id: `zone-${zone.id}`,
      name: zone.name,
      lat: zone.center[0],
      lng: zone.center[1],
      radiusKm: zone.radius_km,
    }))

  const selectedPorts = stops
    .map(code => ports.find(port => port.code === code))
    .filter(Boolean)
    .map(port => ({
      id: `port-${port.code}`,
      name: `${port.name}, ${port.country}`,
      lat: port.lat,
      lng: port.lng,
      radiusKm: 110,
    }))

  const routeMidpoints = (result?.legs || []).map((leg, index) => {
    const point = leg.route[Math.floor(leg.route.length / 2)]
    return {
      id: `leg-${index}`,
      name: `${leg.summary.origin} → ${leg.summary.destination}`,
      lat: point.lat,
      lng: point.lng,
      radiusKm: 150,
    }
  })

  const unique = new Map()
  ;[...weatherZones, ...(routeMidpoints.length ? routeMidpoints : selectedPorts)].forEach(location => {
    unique.set(`${location.lat.toFixed(2)}:${location.lng.toFixed(2)}`, location)
  })
  return [...unique.values()].slice(0, 4)
}

export default function MapView({
  apiKey,
  ports,
  stops,
  result,
  alerts,
  departureTime,
  weatherEnabled,
  showAlerts,
  setShowAlerts,
  soundEnabled,
  audioBlocked,
  onToggleSound,
}) {
  const el = useRef()
  const mapRef = useRef()
  const overlays = useRef([])
  const shipMarkerRef = useRef()
  const shipFrameRef = useRef()
  const [state, setState] = useState(apiKey ? 'loading' : 'nokey')
  const [weatherSamples, setWeatherSamples] = useState([])
  const [weatherStatus, setWeatherStatus] = useState(weatherEnabled ? 'loading' : 'disabled')

  useEffect(() => {
    if (!apiKey || window.google?.maps) {
      if (window.google?.maps) setState('ready')
      return
    }
    const id = 'gmaps-script'
    let script = document.getElementById(id)
    if (!script) {
      script = document.createElement('script')
      script.id = id
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&v=weekly&language=en&region=IN`
      script.async = true
      document.head.appendChild(script)
    }
    script.addEventListener('load', () => setState('ready'))
    script.addEventListener('error', () => setState('error'))
  }, [apiKey])

  useEffect(() => {
    if (!weatherEnabled || !departureTime) {
      setWeatherSamples([])
      setWeatherStatus('disabled')
      return
    }

    const selectedTime = new Date(departureTime)
    if (Number.isNaN(selectedTime.getTime())) {
      setWeatherSamples([])
      setWeatherStatus('error')
      return
    }

    const locations = forecastLocations(alerts, ports, stops, result)
    if (!locations.length) {
      setWeatherSamples([])
      setWeatherStatus('loading')
      return
    }

    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      setWeatherStatus('loading')
      try {
        const responses = await Promise.allSettled(locations.map(async location => ({
          ...location,
          ...(await getEnvironment(location.lat, location.lng, selectedTime.toISOString(), controller.signal)),
        })))
        if (controller.signal.aborted) return
        const samples = responses
          .filter(response => response.status === 'fulfilled')
          .map(response => response.value)
        setWeatherSamples(samples)
        setWeatherStatus(samples.length ? 'ready' : 'error')
      } catch (requestError) {
        if (requestError.name !== 'AbortError') {
          setWeatherSamples([])
          setWeatherStatus('error')
        }
      }
    }, 350)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [alerts, departureTime, ports, result, stops, weatherEnabled])

  useEffect(() => {
    if (state !== 'ready' || !el.current) return
    const g = window.google.maps
    if (!mapRef.current) {
      mapRef.current = new g.Map(el.current, {
        center: { lat: 2, lng: 78 },
        zoom: 3,
        minZoom: 2,
        styles: [
          { featureType: 'poi', stylers: [{ visibility: 'off' }] },
          { featureType: 'road', stylers: [{ visibility: 'off' }] },
          { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#b9dce9' }] },
          { featureType: 'landscape', elementType: 'geometry', stylers: [{ color: '#f4f2e8' }] },
        ],
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
      })
    }

    overlays.current.forEach(overlay => overlay.setMap(null))
    overlays.current = []
    const map = mapRef.current
    const selected = stops.map(code => ports.find(port => port.code === code)).filter(Boolean)

    selected.forEach((port, index) => {
      const marker = new g.Marker({
        map,
        position: port,
        label: { text: String(index + 1), color: '#fff', fontWeight: '700' },
        title: `${index + 1}. ${port.name}`,
        icon: {
          path: g.SymbolPath.CIRCLE,
          fillColor: '#062338',
          fillOpacity: 1,
          strokeColor: '#fff',
          strokeWeight: 2,
          scale: 13,
        },
      })
      overlays.current.push(marker)
    })

    if (showAlerts) {
      alerts.filter(zone => {
        if (zone.type !== 'weather') return true
        return !weatherSamples.some(sample => sample.id === `zone-${zone.id}`)
      }).forEach(zone => {
        const circle = new g.Circle({
          map,
          center: { lat: zone.center[0], lng: zone.center[1] },
          radius: zone.radius_km * 1000,
          fillColor: zoneColor[zone.type],
          fillOpacity: 0.13,
          strokeColor: zoneColor[zone.type],
          strokeOpacity: 0.7,
          strokeWeight: 1.5,
          clickable: true,
          zIndex: zone.type === 'weather' ? 2 : 1,
        })
        const info = new g.InfoWindow({
          content: `<div style="color:#071521;font-family:Inter,Arial,sans-serif;font-size:14px;font-weight:700;line-height:1.45;min-width:240px;padding:4px 2px"><div style="font-size:15px;font-weight:800">${escapeHtml(zone.name)}</div><div style="margin-top:4px;font-weight:700;color:#334155">Prototype/demo alert data · ${escapeHtml(zone.type)}</div></div>`,
        })
        circle.addListener('click', event => {
          info.setPosition(event.latLng)
          info.open(map)
        })
        overlays.current.push(circle)
      })
    }

    weatherSamples.forEach(sample => {
      const color = weatherColor(sample.conditions)
      const circle = new g.Circle({
        map,
        center: { lat: sample.lat, lng: sample.lng },
        radius: sample.radiusKm * 1000,
        fillColor: color,
        fillOpacity: 0.2,
        strokeColor: color,
        strokeOpacity: 0.9,
        strokeWeight: 2,
        clickable: true,
        zIndex: 3,
      })
      const forecastTime = new Date(sample.forecast_time).toLocaleString('en-GB', {
        timeZone: 'UTC',
        dateStyle: 'medium',
        timeStyle: 'short',
      })
      const sourceLabel = sample.fallback_used ? 'Date-indexed fallback' : 'OpenWeather wind + marine fallback'
      const info = new g.InfoWindow({
        content: `<div style="color:#071521;font-family:Inter,Arial,sans-serif;line-height:1.45;min-width:245px;padding:4px 2px"><div style="font-size:15px;font-weight:800">${escapeHtml(sample.name)}</div><div style="margin:5px 0;font-weight:700;color:${color}">${sample.conditions.wave_m.toFixed(1)} m waves · ${sample.conditions.wind_ms.toFixed(1)} m/s wind</div><div style="font-size:12px;color:#475569">${escapeHtml(forecastTime)} UTC<br>${escapeHtml(sourceLabel)}</div></div>`,
      })
      circle.addListener('click', event => {
        info.setPosition(event.latLng)
        info.open(map)
      })
      overlays.current.push(circle)
    })

    if (result) {
      const bounds = new g.LatLngBounds()
      result.legs.forEach(leg => {
        const path = leg.route.map(point => ({ lat: point.lat, lng: point.lng }))
        path.forEach(point => bounds.extend(point))
        const outline = new g.Polyline({ map, path, strokeColor: '#fff', strokeOpacity: 0.95, strokeWeight: 8, zIndex: 4 })
        const line = new g.Polyline({
          map,
          path,
          strokeColor: leg.color,
          strokeOpacity: 1,
          strokeWeight: 4,
          zIndex: 5,
          icons: [{
            icon: { path: g.SymbolPath.FORWARD_CLOSED_ARROW, scale: 2, strokeColor: leg.color },
            offset: '3%',
            repeat: '80px',
          }],
        })
        overlays.current.push(outline, line)
      })
      map.fitBounds(bounds, 48)
    } else if (selected.length) {
      const bounds = new g.LatLngBounds()
      selected.forEach(port => bounds.extend({ lat: port.lat, lng: port.lng }))
      map.fitBounds(bounds, 80)
    }
  }, [alerts, ports, result, showAlerts, state, stops, weatherSamples])

  useEffect(() => {
    if (shipFrameRef.current) window.cancelAnimationFrame(shipFrameRef.current)
    shipMarkerRef.current?.setMap(null)
    shipFrameRef.current = undefined
    shipMarkerRef.current = undefined

    if (state !== 'ready' || !mapRef.current || !result?.combined_route?.length) return
    const g = window.google.maps
    const path = result.combined_route
      .map(point => ({ lat: Number(point.lat), lng: Number(point.lng) }))
      .filter(point => Number.isFinite(point.lat) && Number.isFinite(point.lng))

    const segments = []
    let totalDistance = 0
    for (let index = 0; index < path.length - 1; index += 1) {
      const distance = segmentDistance(path[index], path[index + 1])
      if (distance <= 0) continue
      segments.push({ start: path[index], end: path[index + 1], distance, offset: totalDistance })
      totalDistance += distance
    }
    if (!segments.length || totalDistance <= 0) return

    const icon = rotation => ({
      path: SHIP_SYMBOL_PATH,
      fillColor: '#f97316',
      fillOpacity: 1,
      strokeColor: '#ffffff',
      strokeOpacity: 1,
      strokeWeight: 2.4,
      scale: 1.15,
      rotation,
      anchor: new g.Point(0, 0),
    })
    const marker = new g.Marker({
      map: mapRef.current,
      position: segments[0].start,
      icon: icon(segmentBearing(segments[0].start, segments[0].end)),
      title: 'Ship underway on the optimized route',
      zIndex: 1000,
      optimized: true,
    })
    shipMarkerRef.current = marker

    const travelDuration = Math.min(42000, Math.max(18000, totalDistance * 7))
    const destinationPause = 1400
    const cycleDuration = travelDuration + destinationPause
    let activeElapsed = 0
    let previousFrame
    let activeSegment
    const animate = timestamp => {
      if (shipMarkerRef.current !== marker) return
      if (previousFrame !== undefined) activeElapsed += Math.min(100, Math.max(0, timestamp - previousFrame))
      previousFrame = timestamp
      const elapsed = activeElapsed % cycleDuration
      const progress = Math.min(elapsed, travelDuration) / travelDuration
      const targetDistance = progress * totalDistance
      const segment = segments.find(candidate => targetDistance <= candidate.offset + candidate.distance) || segments.at(-1)
      const segmentProgress = Math.min(1, Math.max(0, (targetDistance - segment.offset) / segment.distance))
      const longitudeDelta = (((segment.end.lng - segment.start.lng) + 540) % 360) - 180
      const longitude = ((segment.start.lng + longitudeDelta * segmentProgress + 540) % 360) - 180
      marker.setPosition({
        lat: segment.start.lat + (segment.end.lat - segment.start.lat) * segmentProgress,
        lng: longitude,
      })
      if (activeSegment !== segment) {
        marker.setIcon(icon(segmentBearing(segment.start, segment.end)))
        activeSegment = segment
      }
      shipFrameRef.current = window.requestAnimationFrame(animate)
    }
    shipFrameRef.current = window.requestAnimationFrame(animate)

    return () => {
      if (shipFrameRef.current) window.cancelAnimationFrame(shipFrameRef.current)
      marker.setMap(null)
      if (shipMarkerRef.current === marker) shipMarkerRef.current = undefined
      shipFrameRef.current = undefined
    }
  }, [result, state])

  const forecastTimeLabel = departureTime && !Number.isNaN(new Date(departureTime).getTime())
    ? new Date(departureTime).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
    : 'Select a valid departure time'
  const maximumWave = weatherSamples.length ? Math.max(...weatherSamples.map(sample => sample.conditions.wave_m)) : 0
  const maximumWind = weatherSamples.length ? Math.max(...weatherSamples.map(sample => sample.conditions.wind_ms)) : 0

  return <main className="mapWrap">
    <div className="mapCanvas" ref={el} />
    {state !== 'ready' && <div className="mapFallback">
      <MapIcon />
      <h2>{state === 'nokey' ? 'Google Maps key required' : 'Loading navigation chart…'}</h2>
      <p>{state === 'nokey' ? 'Add a browser-restricted key to .env, then restart the server. Route calculations remain available.' : 'Connecting to Google Maps visualization.'}</p>
      <div className="oceanLines" />
    </div>}
    <div className="mapTools">
      <button className={showAlerts ? 'active' : ''} onClick={() => setShowAlerts(!showAlerts)}><ShieldAlert /> Alert zones</button>
      <button className={`${soundEnabled ? 'active' : ''} ${audioBlocked ? 'attention' : ''}`} onClick={onToggleSound} aria-pressed={soundEnabled}>{soundEnabled ? <Volume2 /> : <VolumeX />}{audioBlocked ? 'Enable sound' : soundEnabled ? 'Voyage sound' : 'Sound off'}</button>
      <span><Layers /> LIGHT CHART</span>
    </div>
    {result && state === 'ready' && <div className="voyageMotion"><Ship /><span><b>Ship underway</b><small>Following the optimized sea route</small></span></div>}
    {weatherEnabled && <div className={`forecastStatus forecast-${weatherStatus}`}>
      <CloudSun />
      <span>
        <b>{weatherStatus === 'loading' ? 'Updating forecast…' : weatherStatus === 'error' ? 'Forecast unavailable' : forecastTimeLabel}</b>
        <small>{weatherStatus === 'ready' ? `${maximumWave.toFixed(1)} m max wave · ${maximumWind.toFixed(1)} m/s max wind` : 'Weather changes with the selected departure time'}</small>
      </span>
    </div>}
    <div className="legend">
      <b>ALERTS + TIME-INDEXED WEATHER</b>
      {Object.entries(zoneColor).map(([key, value]) => <span key={key}><i style={{ background: value }} />{key}</span>)}
    </div>
  </main>
}
