import React, { useState, useEffect } from 'react'
import { Activity, Shield, Zap, TrendingUp } from 'lucide-react'
import { factionWarfareApi } from '../services/api'

interface FactionWarfareOverview {
  timestamp: string
  minmatar: {
    systems_controlled: number
    control_percentage: number
    kills_24h: number
    efficiency: number
  }
  amarr: {
    systems_controlled: number
    control_percentage: number
    kills_24h: number
    efficiency: number
  }
  warzone: {
    total_systems: number
    contested_systems: number
    activity_index: number
  }
}

export const Dashboard: React.FC = () => {
  const [overview, setOverview] = useState<FactionWarfareOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        setLoading(true)
        const response = await factionWarfareApi.getOverview()
        setOverview(response.data)
        setError(null)
      } catch (err) {
        setError('Failed to fetch faction warfare overview')
        console.error('Error fetching overview:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchOverview()
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchOverview, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-400">Loading faction warfare data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-400">{error}</div>
      </div>
    )
  }

  if (!overview) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-400">No data available</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-2">
          EVE Wargames Dashboard
        </h1>
        <p className="text-gray-400">
          Minmatar vs Amarr Faction Warfare Analytics
        </p>
        <p className="text-sm text-gray-500 mt-2">
          Last updated: {new Date(overview.timestamp).toLocaleString()}
        </p>
      </div>

      {/* Faction Control Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Minmatar Card */}
        <div className="card border-l-4 faction-minmatar">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-red-400">
              Minmatar Republic
            </h2>
            <Shield className="text-red-400" size={24} />
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-300">Systems Controlled:</span>
              <span className="font-semibold text-white">
                {overview.minmatar.systems_controlled}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Control Percentage:</span>
              <span className="font-semibold text-white">
                {overview.minmatar.control_percentage.toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Kills (24h):</span>
              <span className="font-semibold text-white">
                {overview.minmatar.kills_24h}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Efficiency:</span>
              <span className="font-semibold text-white">
                {(overview.minmatar.efficiency * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Amarr Card */}
        <div className="card border-l-4 faction-amarr">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-yellow-400">
              Amarr Empire
            </h2>
            <Shield className="text-yellow-400" size={24} />
          </div>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-300">Systems Controlled:</span>
              <span className="font-semibold text-white">
                {overview.amarr.systems_controlled}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Control Percentage:</span>
              <span className="font-semibold text-white">
                {overview.amarr.control_percentage.toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Kills (24h):</span>
              <span className="font-semibold text-white">
                {overview.amarr.kills_24h}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-300">Efficiency:</span>
              <span className="font-semibold text-white">
                {(overview.amarr.efficiency * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Warzone Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Total Systems</h3>
            <Activity className="text-blue-400" size={20} />
          </div>
          <div className="text-3xl font-bold text-white">
            {overview.warzone.total_systems}
          </div>
          <div className="text-sm text-gray-400 mt-2">
            Systems in warzone
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Contested</h3>
            <Zap className="text-orange-400" size={20} />
          </div>
          <div className="text-3xl font-bold text-orange-400">
            {overview.warzone.contested_systems}
          </div>
          <div className="text-sm text-gray-400 mt-2">
            Systems under contest
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Activity Index</h3>
            <TrendingUp className="text-green-400" size={20} />
          </div>
          <div className="text-3xl font-bold text-green-400">
            {overview.warzone.activity_index.toFixed(1)}
          </div>
          <div className="text-sm text-gray-400 mt-2">
            Warzone activity level
          </div>
        </div>
      </div>

      {/* Control Visualization */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">
          Warzone Control Distribution
        </h3>
        <div className="space-y-4">
          {/* Combined Progress Bar */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <div className="flex items-center space-x-4">
                <span className="text-red-400">
                  Minmatar: {overview.minmatar.control_percentage.toFixed(1)}%
                </span>
                <span className="text-yellow-400">
                  Amarr: {overview.amarr.control_percentage.toFixed(1)}%
                </span>
              </div>
              <span className="text-gray-400 text-xs">
                {overview.warzone.total_systems} systems total
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-4 overflow-hidden">
              <div className="flex h-full">
                <div
                  className="bg-red-500 transition-all duration-500 flex items-center justify-center"
                  style={{ width: `${overview.minmatar.control_percentage}%` }}
                >
                  {overview.minmatar.control_percentage > 15 && (
                    <span className="text-white text-xs font-medium">
                      {overview.minmatar.systems_controlled}
                    </span>
                  )}
                </div>
                <div
                  className="bg-yellow-500 transition-all duration-500 flex items-center justify-center"
                  style={{ width: `${overview.amarr.control_percentage}%` }}
                >
                  {overview.amarr.control_percentage > 15 && (
                    <span className="text-black text-xs font-medium">
                      {overview.amarr.systems_controlled}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>Minmatar: {overview.minmatar.systems_controlled} systems</span>
              <span>Amarr: {overview.amarr.systems_controlled} systems</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
