import React, { useState, useRef, useEffect } from 'react'
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'
import { mapSystems } from '../data/mapSystems'
import './MapView.css'

interface System {
  system_id: number
  name: string
  security_status: number
  controlling_faction_id: number
  contested: boolean
  capture_percent: number
  advantage_percent: number
  minmatar_advantage: number
  amarr_advantage: number
  updated_at: string
  frontline_classification?: 'frontline' | 'command_operations' | 'rearguard'
}

interface MapViewProps {
  systems: System[]
  selectedSystemId: number | null
  onSystemSelect: (systemId: number) => void
}

export const MapView: React.FC<MapViewProps> = ({ systems, selectedSystemId, onSystemSelect }) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // Create a map of system IDs to system data for quick lookup
  const systemsMap = systems.reduce((acc, system) => {
    acc[system.system_id] = system
    return acc
  }, {} as Record<number, System>)

  const handleSystemClick = (systemId: number) => {
    onSystemSelect(systemId)
  }

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 3))
  }

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev / 1.2, 0.5))
  }

  const handleReset = () => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === svgRef.current) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const getSystemClasses = (systemId: number) => {
    const system = systemsMap[systemId]
    if (!system) return 'system-group'

    const factionClass = system.controlling_faction_id === 500002 ? 'system-minmatar' : 'system-amarr'
    const contestedClass = system.contested ? 'system-contested' : ''
    const selectedClass = selectedSystemId === systemId ? 'selected' : ''
    
    // Add frontline classification class for opacity styling
    const frontlineClass = system.frontline_classification ? `system-${system.frontline_classification}` : ''
    
    return `system-group ${factionClass} ${contestedClass} ${selectedClass} ${frontlineClass}`.trim()
  }

  // Calculate the centroid (center point) of an SVG path
  const calculatePathCentroid = (pathData: string) => {
    // Parse the path data to extract coordinates
    const coords = pathData.match(/[0-9.]+/g)?.map(Number) || []
    
    if (coords.length < 4) return { x: 0, y: 0 }
    
    // Calculate centroid by averaging all x and y coordinates
    let sumX = 0, sumY = 0, count = 0
    
    for (let i = 0; i < coords.length; i += 2) {
      if (i + 1 < coords.length) {
        sumX += coords[i]
        sumY += coords[i + 1]
        count++
      }
    }
    
    return {
      x: count > 0 ? sumX / count : 0,
      y: count > 0 ? sumY / count : 0
    }
  }

  // SVG content extracted from map.html - this is a simplified version
  // In a real implementation, you'd want to load this dynamically
  const renderSystemGroup = (systemId: number, pathData: string, title: string) => {
    const classes = getSystemClasses(systemId)
    const centroid = calculatePathCentroid(pathData)
    
    return (
      <g
        key={systemId}
        id={`system-${systemId}`}
        className={classes}
        onClick={() => handleSystemClick(systemId)}
      >
        <path
          d={pathData}
          className="system-fill"
        >
          <title>{title}</title>
        </path>
        <path
          d={pathData}
          className="system-border"
        />
        <text
          x={centroid.x}
          y={centroid.y}
          className="system-label"
          textAnchor="middle"
          dominantBaseline="central"
        >
          {title}
        </text>
      </g>
    )
  }

  return (
    <div className="warzone-map-container">
      {/* Map Controls */}
      <div className="map-controls">
        <button className="map-control-btn" onClick={handleZoomIn} title="Zoom In">
          <ZoomIn className="w-4 h-4" />
        </button>
        <button className="map-control-btn" onClick={handleZoomOut} title="Zoom Out">
          <ZoomOut className="w-4 h-4" />
        </button>
        <button className="map-control-btn" onClick={handleReset} title="Reset View">
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Map Legend */}
      <div className="map-legend">
        <div className="legend-item">
          <div className="legend-color legend-minmatar"></div>
          <span>Minmatar Republic</span>
        </div>
        <div className="legend-item">
          <div className="legend-color legend-amarr"></div>
          <span>Amarr Empire</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'transparent', border: '1px dashed #666' }}></div>
          <span>Contested</span>
        </div>
      </div>

      {/* SVG Map */}
      <svg
        ref={svgRef}
        className="warzone-map-svg"
        viewBox="0 0 10000 12000"
        preserveAspectRatio="xMidYMid meet"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: 'center'
        }}
      >
        {/* Define filters for visual effects */}
        <defs>
          <filter id="fill-filter">
            <feGaussianBlur stdDeviation="1" />
          </filter>
          <filter id="border-filter">
            <feDropShadow dx="0" dy="0" stdDeviation="2" floodOpacity="0.3" />
          </filter>
        </defs>

        {/* Render all systems from the map data */}
        {mapSystems.map(system => renderSystemGroup(system.id, system.pathData, system.name))}
      </svg>
    </div>
  )
}
