import React, { useState, useEffect } from 'react'
import { Shield, AlertTriangle, Clock, Users, TrendingUp, Calendar, Building, Crown, RefreshCw } from 'lucide-react'
import { systemsApi, frontlinesApi } from '../services/api'
import { PlayerCard, CorporationCard, AllianceCard, EntityList } from './EntityCards'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend
} from 'recharts'

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

interface TrendData {
  system: {
    system_id: number
    name: string
  }
  period: {
    start: string
    end: string
    hours: number
  }
  data: Array<{
    timestamp: string
    controlling_faction_id: number
    contested: boolean
    capture_percent: number
    advantage_percent: number
    minmatar_advantage: number
    amarr_advantage: number
  }>
}

interface KillmailStats {
  system: {
    system_id: number
    name: string
  }
  time_window_hours: number
  most_active: {
    player: {
      character_id: number
      character_name: string
      kills: number
      isk_killed: number
    } | null
    corporation: {
      corporation_id: number
      corporation_name: string
      ticker: string
      kills: number
      isk_killed: number
      unique_players: number
    } | null
    alliance: {
      alliance_id: number
      alliance_name: string
      ticker: string
      kills: number
      isk_killed: number
      unique_players: number
      unique_corporations: number
    } | null
  }
  top_performers: {
    players: Array<{
      character_id: number
      character_name: string
      kills: number
      isk_killed: number
    }>
    corporations: Array<{
      corporation_id: number
      corporation_name: string
      ticker: string
      kills: number
      isk_killed: number
      unique_players: number
    }>
    alliances: Array<{
      alliance_id: number
      alliance_name: string
      ticker: string
      kills: number
      isk_killed: number
      unique_players: number
      unique_corporations: number
    }>
  }
  generated_at: string
}

interface SystemSidebarProps {
  selectedSystem: System | null
  onClose: () => void
  isFullscreen?: boolean
}

export const SystemSidebar: React.FC<SystemSidebarProps> = ({ selectedSystem, onClose, isFullscreen = false }) => {
  const sidebarWidthClass = isFullscreen ? 'w-full h-full' : 'w-80'
  
  // Enhanced data state
  const [trendData, setTrendData] = useState<TrendData | null>(null)
  const [killmailStats, setKillmailStats] = useState<KillmailStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [timeRange, setTimeRange] = useState(24)
  const [activeTab, setActiveTab] = useState<'overview' | 'trends' | 'pvp'>('overview')

  // Fetch detailed data when system changes
  useEffect(() => {
    if (selectedSystem) {
      fetchDetailedData()
    } else {
      // Clear data when no system selected
      setTrendData(null)
      setKillmailStats(null)
    }
  }, [selectedSystem, timeRange])

  const fetchDetailedData = async () => {
    if (!selectedSystem) return

    try {
      setLoading(true)
      const [trendsResponse, killmailStatsResponse] = await Promise.all([
        systemsApi.getSystemTrends(selectedSystem.system_id, timeRange),
        systemsApi.getSystemKillmailStats(selectedSystem.system_id, timeRange).catch(() => null)
      ])

      setTrendData(trendsResponse.data)
      setKillmailStats(killmailStatsResponse?.data || null)
    } catch (err) {
      console.error('Error fetching detailed system data:', err)
    } finally {
      setLoading(false)
    }
  }
  
  if (!selectedSystem) {
    return (
      <div className={`${sidebarWidthClass} bg-gray-900 border-l border-gray-700 p-6 flex items-center justify-center`}>
        <div className="text-center text-gray-400">
          <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium mb-2">Select a System</p>
          <p className="text-sm">Click on any system on the map to view its details</p>
        </div>
      </div>
    )
  }

  const getFactionName = (factionId: number) => {
    switch (factionId) {
      case 500002: return 'Minmatar Republic'
      case 500003: return 'Amarr Empire'
      default: return 'Unknown'
    }
  }

  const formatISK = (value: number) => {
    if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
    if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`
    if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`
    return value.toFixed(0)
  }

  const formatChartData = (data: TrendData['data']) => {
    return data.map(point => ({
      timestamp: new Date(point.timestamp).toLocaleTimeString([], { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      }),
      fullTimestamp: point.timestamp,
      capture_percent: point.capture_percent,
      advantage_percent: point.advantage_percent,
      contested: point.contested,
      controlling_faction: getFactionName(point.controlling_faction_id)
    }))
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg">
          <p className="text-white font-medium">{label}</p>
          <p className="text-blue-400">
            Capture: {payload.find((p: any) => p.dataKey === 'capture_percent')?.value?.toFixed(1)}%
          </p>
          <p className="text-purple-400">
            Advantage: {payload.find((p: any) => p.dataKey === 'advantage_percent')?.value?.toFixed(1)}%
          </p>
          <p className="text-gray-300">
            Status: {data.contested ? 'Contested' : 'Stable'}
          </p>
        </div>
      )
    }
    return null
  }

  const getFactionColor = (factionId: number) => {
    switch (factionId) {
      case 500002: return 'text-red-400'
      case 500003: return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  const getAdvantageBarColor = (system: System) => {
    if (system.minmatar_advantage > system.amarr_advantage) {
      return 'bg-red-400'
    } else if (system.amarr_advantage > system.minmatar_advantage) {
      return 'bg-yellow-400'
    } else {
      return 'bg-gray-500'
    }
  }

  const getSecurityColor = (security: number) => {
    if (security >= 0.5) return 'text-green-400'
    if (security >= 0.1) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getFrontlineClassificationInfo = (classification?: string, factionId?: number) => {
    const isMinmatar = factionId === 500002
    const isAmarr = factionId === 500003
    
    switch (classification) {
      case 'frontline':
        return {
          label: 'Frontline',
          color: isMinmatar ? 'text-minmatar-red' : isAmarr ? 'text-amarr-yellow' : 'text-red-400',
          bgColor: isMinmatar ? 'bg-minmatar-frontline' : isAmarr ? 'bg-amarr-frontline' : 'bg-red-500/20',
          icon: '🔴',
          description: 'System adjacent to enemy-controlled territory'
        }
      case 'command_operations':
        return {
          label: 'Command Operations',
          color: isMinmatar ? 'text-minmatar-red' : isAmarr ? 'text-amarr-yellow' : 'text-orange-400',
          bgColor: isMinmatar ? 'bg-minmatar-command' : isAmarr ? 'bg-amarr-command' : 'bg-orange-500/20',
          icon: '🟡',
          description: 'System adjacent to frontline systems'
        }
      case 'rearguard':
        return {
          label: 'Rearguard',
          color: isMinmatar ? 'text-minmatar-red' : isAmarr ? 'text-amarr-yellow' : 'text-green-400',
          bgColor: isMinmatar ? 'bg-minmatar-rearguard' : isAmarr ? 'bg-amarr-rearguard' : 'bg-green-500/20',
          icon: '🟢',
          description: 'Safe zone away from immediate battle'
        }
      default:
        return {
          label: 'Unknown',
          color: 'text-gray-400',
          bgColor: 'bg-gray-500/20',
          icon: '⚪',
          description: 'Classification not available'
        }
    }
  }

  return (
    <div className={`${sidebarWidthClass} bg-gray-900 border-l border-gray-700 flex flex-col overflow-hidden`}>
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-700">
        <h3 className="text-xl font-bold text-white">System Details</h3>
        <div className="flex items-center gap-2">
          {loading && <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />}
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ×
          </button>
        </div>
      </div>

      {/* System Name & Basic Info */}
      <div className="p-6 border-b border-gray-700">
        <h2 className="text-2xl font-bold text-white mb-2">{selectedSystem.name}</h2>
        <div className="flex items-center gap-4 text-sm text-gray-400 mb-4">
          <span>ID: {selectedSystem.system_id}</span>
          <span className={getSecurityColor(selectedSystem.security_status)}>
            Sec: {selectedSystem.security_status.toFixed(1)}
          </span>
        </div>

        {/* Status & Faction */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              {selectedSystem.contested ? (
                <>
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  <span className="text-orange-400 text-sm">Contested</span>
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4 text-green-500" />
                  <span className="text-green-400 text-sm">Stable</span>
                </>
              )}
            </div>
          </div>
          <div>
            <div className={`text-sm font-medium ${getFactionColor(selectedSystem.controlling_faction_id)}`}>
              {getFactionName(selectedSystem.controlling_faction_id).replace(' Republic', '').replace(' Empire', '')}
            </div>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex gap-2 mb-4">
          {[6, 12, 24, 48].map((hours) => (
            <button
              key={hours}
              onClick={() => setTimeRange(hours)}
              className={`px-3 py-1 text-xs rounded ${
                timeRange === hours
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {hours}h
            </button>
          ))}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-700">
        {[
          { id: 'overview', label: 'Overview', icon: Shield },
          { id: 'trends', label: 'Trends', icon: TrendingUp },
          { id: 'pvp', label: 'PvP', icon: Users }
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as any)}
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
              activeTab === id
                ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-800'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'overview' && (
          <div className="p-6 space-y-6">
            {/* Frontline Classification */}
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">Frontline Classification</h4>
              {(() => {
                const frontlineInfo = getFrontlineClassificationInfo(selectedSystem.frontline_classification, selectedSystem.controlling_faction_id)
                return (
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{frontlineInfo.icon}</span>
                      <span className={`font-semibold px-3 py-1 rounded-full text-xs ${frontlineInfo.bgColor} ${frontlineInfo.color}`}>
                        {frontlineInfo.label}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">{frontlineInfo.description}</p>
                  </div>
                )
              })()}
            </div>

            {/* Capture Progress */}
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">Capture Progress</h4>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${Math.max(0, Math.min(100, selectedSystem.capture_percent))}%` }}
                  ></div>
                </div>
                <span className="text-sm text-gray-300 w-12">
                  {selectedSystem.capture_percent.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Advantage */}
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">Faction Advantage</h4>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div 
                    className={`${getAdvantageBarColor(selectedSystem)} h-2 rounded-full transition-all duration-300`}
                    style={{ width: `${Math.max(0, Math.min(100, selectedSystem.advantage_percent))}%` }}
                  ></div>
                </div>
                <span className="text-sm text-gray-300 w-12">
                  {selectedSystem.advantage_percent.toFixed(1)}%
                </span>
              </div>
              
              {/* Detailed advantage breakdown */}
              <div className="mt-3 space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-red-400">Minmatar:</span>
                  <span className="text-white">{selectedSystem.minmatar_advantage.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-yellow-400">Amarr:</span>
                  <span className="text-white">{selectedSystem.amarr_advantage.toFixed(1)}%</span>
                </div>
              </div>
            </div>

            {/* Last Updated */}
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">Last Updated</h4>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Clock className="w-4 h-4" />
                <span>{new Date(selectedSystem.updated_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'trends' && (
          <div className="p-6">
            {trendData && trendData.data.length > 0 ? (
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-300">Historical Trends ({timeRange}h)</h4>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={formatChartData(trendData.data)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="timestamp" 
                        stroke="#9CA3AF"
                        fontSize={10}
                        interval="preserveStartEnd"
                      />
                      <YAxis 
                        stroke="#9CA3AF"
                        fontSize={10}
                        domain={[0, 100]}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="capture_percent" 
                        stroke="#3B82F6" 
                        strokeWidth={2}
                        name="Capture %"
                        dot={{ fill: '#3B82F6', strokeWidth: 2, r: 2 }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="advantage_percent" 
                        stroke="#8B5CF6" 
                        strokeWidth={2}
                        name="Advantage %"
                        dot={{ fill: '#8B5CF6', strokeWidth: 2, r: 2 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Calendar className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400 text-sm">No trend data available for the selected time range.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'pvp' && (
          <div className="p-6">
            {killmailStats ? (
              <div className="space-y-6">
                <h4 className="text-sm font-medium text-gray-300">PvP Activity (Last {killmailStats.time_window_hours}h)</h4>
                
                {/* Top Players */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Users className="w-4 h-4 text-blue-500" />
                    <h5 className="text-sm font-medium text-white">Top Players</h5>
                  </div>
                  {killmailStats.top_performers.players.length > 0 ? (
                    <div className="space-y-2">
                      {killmailStats.top_performers.players.slice(0, 5).map((player, index) => (
                        <div key={player.character_id} className="flex items-center justify-between p-2 bg-gray-800 rounded text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400 w-4">#{index + 1}</span>
                            <span className="text-white">{player.character_name}</span>
                          </div>
                          <div className="text-right">
                            <div className="text-white">{player.kills} kills</div>
                            <div className="text-gray-400 text-xs">{formatISK(player.isk_killed)} ISK</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-400 text-sm">No player data available</p>
                  )}
                </div>

                {/* Top Corporations */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Building className="w-4 h-4 text-purple-500" />
                    <h5 className="text-sm font-medium text-white">Top Corporations</h5>
                  </div>
                  {killmailStats.top_performers.corporations.length > 0 ? (
                    <div className="space-y-2">
                      {killmailStats.top_performers.corporations.slice(0, 5).map((corp, index) => (
                        <div key={corp.corporation_id} className="flex items-center justify-between p-2 bg-gray-800 rounded text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400 w-4">#{index + 1}</span>
                            <div>
                              <div className="text-white">{corp.corporation_name}</div>
                              <div className="text-gray-400 text-xs">[{corp.ticker}] • {corp.unique_players} pilots</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-white">{corp.kills} kills</div>
                            <div className="text-gray-400 text-xs">{formatISK(corp.isk_killed)} ISK</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-400 text-sm">No corporation data available</p>
                  )}
                </div>

                {/* Top Alliances */}
                {killmailStats.top_performers.alliances.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Crown className="w-4 h-4 text-yellow-500" />
                      <h5 className="text-sm font-medium text-white">Top Alliances</h5>
                    </div>
                    <div className="space-y-2">
                      {killmailStats.top_performers.alliances.slice(0, 3).map((alliance, index) => (
                        <div key={alliance.alliance_id} className="flex items-center justify-between p-2 bg-gray-800 rounded text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400 w-4">#{index + 1}</span>
                            <div>
                              <div className="text-white">{alliance.alliance_name}</div>
                              <div className="text-gray-400 text-xs">[{alliance.ticker}] • {alliance.unique_corporations} corps</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-white">{alliance.kills} kills</div>
                            <div className="text-gray-400 text-xs">{formatISK(alliance.isk_killed)} ISK</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="text-center pt-4 border-t border-gray-700">
                  <p className="text-gray-400 text-xs">
                    Data updated: {new Date(killmailStats.generated_at).toLocaleString()}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Users className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400 text-sm">No PvP data available for the selected time range.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="border-t border-gray-700 p-4">
        <button
          onClick={() => window.open(`/systems/${selectedSystem.system_id}`, '_blank')}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg transition-colors text-sm"
        >
          View Full System Page
        </button>
      </div>
    </div>
  )
}
