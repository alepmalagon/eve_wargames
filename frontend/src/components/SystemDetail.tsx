import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { systemsApi, frontlinesApi } from '../services/api'
import { 
  ArrowLeft, 
  AlertTriangle, 
  Shield, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  RefreshCw,
  Calendar,
  Users,
  Building,
  Crown
} from 'lucide-react'
import { PlayerCard, CorporationCard, AllianceCard, EntityList } from './EntityCards'
import { 
  getCorporationLogoUrl, 
  getAllianceLogoUrl, 
  getFallbackImageUrl 
} from '../utils/eveImages'
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

interface SystemDetails {
  system_id: number
  name: string
  security_status: number
  controlling_faction_id: number
  contested: boolean
  capture_percent: number
  advantage_percent: number
  minmatar_advantage: number
  amarr_advantage: number
  created_at: string
  updated_at: string
  frontline_classification?: 'frontline' | 'command_operations' | 'rearguard'
  adjacent_systems?: Array<{
    system_id: number
    name: string
    controlling_faction_id: number
    classification: string
  }>
  recent_snapshots: Array<{
    timestamp: string
    controlling_faction_id: number
    contested: boolean
    capture_percent: number
    advantage_percent: number
    minmatar_advantage: number
    amarr_advantage: number
  }>
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

interface StagedCorporation {
  corporation_id: number
  corporation_name: string
  ticker: string
  alliance_id: number | null
  alliance_name: string | null
  alliance_ticker: string | null
  system_id: number
  system_name: string
  kills: number
  isk_killed: number
}

interface StagedCorporationsData {
  system: {
    system_id: number
    name: string
  }
  time_window_hours: number
  staged_corporations: StagedCorporation[]
  total_staged_corporations: number
  generated_at: string
}

// Component for displaying entity images with error handling
const EntityImage: React.FC<{
  src: string
  fallbackSrc: string
  alt: string
  className?: string
}> = ({ src, fallbackSrc, alt, className = "" }) => {
  const [imageError, setImageError] = useState(false)
  const [imageLoading, setImageLoading] = useState(true)

  const handleImageLoad = () => {
    setImageLoading(false)
  }

  const handleImageError = () => {
    setImageError(true)
    setImageLoading(false)
  }

  return (
    <div className={`relative ${className}`}>
      {imageLoading && (
        <div className="absolute inset-0 bg-gray-700 animate-pulse rounded-full"></div>
      )}
      <img
        src={imageError ? fallbackSrc : src}
        alt={alt}
        className={`w-full h-full object-cover rounded-full ${imageLoading ? 'opacity-0' : 'opacity-100'} transition-opacity duration-200`}
        onLoad={handleImageLoad}
        onError={handleImageError}
      />
    </div>
  )
}

export const SystemDetail: React.FC = () => {
  const { systemId } = useParams<{ systemId: string }>()
  const navigate = useNavigate()
  const [systemDetails, setSystemDetails] = useState<SystemDetails | null>(null)
  const [trendData, setTrendData] = useState<TrendData | null>(null)
  const [killmailStats, setKillmailStats] = useState<KillmailStats | null>(null)
  const [stagedCorporations, setStagedCorporations] = useState<StagedCorporationsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState(24)
  const [stagingTimeRange, setStagingTimeRange] = useState(168) // 7 days for staging analysis
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (systemId) {
      fetchSystemData()
    }
  }, [systemId, timeRange, stagingTimeRange])

  const fetchSystemData = async () => {
    if (!systemId) return

    try {
      setLoading(true)
      setError(null)

      const [detailsResponse, trendsResponse, killmailStatsResponse, stagedCorpsResponse, frontlineResponse] = await Promise.all([
        systemsApi.getSystemDetails(parseInt(systemId)),
        systemsApi.getSystemTrends(parseInt(systemId), timeRange),
        systemsApi.getSystemKillmailStats(parseInt(systemId), timeRange).catch(() => null),
        systemsApi.getStagedCorporations(parseInt(systemId), stagingTimeRange).catch(() => null),
        frontlinesApi.getSystemInfo(parseInt(systemId)).catch(err => {
          console.warn('Failed to fetch frontline data:', err)
          return null
        })
      ])

      // Merge frontline data with system details
      const systemDetailsWithFrontline = {
        ...detailsResponse.data,
        frontline_classification: frontlineResponse?.data?.classification,
        adjacent_systems: frontlineResponse?.data?.adjacent_systems
      }

      setSystemDetails(systemDetailsWithFrontline)
      setTrendData(trendsResponse.data)
      setKillmailStats(killmailStatsResponse?.data || null)
      setStagedCorporations(stagedCorpsResponse?.data || null)
    } catch (err) {
      setError('Failed to fetch system data')
      console.error('Error fetching system data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchSystemData()
    setRefreshing(false)
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

  const getFrontlineClassificationInfo = (classification?: string) => {
    switch (classification) {
      case 'frontline':
        return {
          label: 'Frontline',
          color: 'text-red-400',
          bgColor: 'bg-red-500/20',
          icon: '🔴',
          description: 'System adjacent to enemy-controlled territory'
        }
      case 'command_operations':
        return {
          label: 'Command Operations',
          color: 'text-orange-400',
          bgColor: 'bg-orange-500/20',
          icon: '🟡',
          description: 'System adjacent to frontline systems'
        }
      case 'rearguard':
        return {
          label: 'Rearguard',
          color: 'text-green-400',
          bgColor: 'bg-green-500/20',
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

  const getFactionColor = (factionId: number) => {
    switch (factionId) {
      case 500002: return 'text-minmatar-red'
      case 500003: return 'text-amarr-yellow'
      default: return 'text-gray-400'
    }
  }

  // Function to get advantage bar color based on leading faction
  const getAdvantageBarColor = (snapshot: { minmatar_advantage: number; amarr_advantage: number }) => {
    if (snapshot.minmatar_advantage > snapshot.amarr_advantage) {
      return 'bg-red-400' // Minmatar color - rgb(248 113 113)
    } else if (snapshot.amarr_advantage > snapshot.minmatar_advantage) {
      return 'bg-yellow-400' // Amarr color - rgb(250 204 21)
    } else {
      return 'bg-gray-500' // Neutral/equal
    }
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
          <p className="text-gray-300">
            Faction: {data.controlling_faction}
          </p>
        </div>
      )
    }
    return null
  }

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/systems')}
            className="btn btn-secondary"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Systems
          </button>
          <h1 className="text-4xl font-bold text-white">Loading System...</h1>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card">
              <div className="animate-pulse">
                <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
                <div className="h-8 bg-gray-700 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error || !systemDetails) {
    return (
      <div className="space-y-8">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/systems')}
            className="btn btn-secondary"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Systems
          </button>
          <h1 className="text-4xl font-bold text-white">System Not Found</h1>
        </div>
        <div className="card">
          <div className="text-center py-8">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-400 mb-4">{error || 'System not found'}</p>
            <button 
              onClick={handleRefresh}
              className="btn btn-primary"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  const chartData = trendData ? formatChartData(trendData.data) : []

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate('/systems')}
            className="btn btn-secondary"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Systems
          </button>
          <div>
            <h1 className="text-4xl font-bold text-white">{systemDetails.name}</h1>
            <p className="text-gray-400">System ID: {systemDetails.system_id}</p>
          </div>
        </div>
        <button 
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn btn-primary"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Current Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <div className="card">
          <div className="flex items-center gap-3">
            <Shield className={`w-8 h-8 ${systemDetails.contested ? 'text-orange-500' : 'text-green-500'}`} />
            <div>
              <p className="text-gray-400 text-sm">Status</p>
              <p className={`font-bold text-lg ${systemDetails.contested ? 'text-orange-400' : 'text-green-400'}`}>
                {systemDetails.contested ? 'Contested' : 'Stable'}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold ${
              systemDetails.controlling_faction_id === 500002 ? 'bg-minmatar-red' : 'bg-amarr-yellow text-black'
            }`}>
              {systemDetails.controlling_faction_id === 500002 ? 'M' : 'A'}
            </div>
            <div>
              <p className="text-gray-400 text-sm">Controlling Faction</p>
              <p className={`font-bold text-lg ${getFactionColor(systemDetails.controlling_faction_id)}`}>
                {getFactionName(systemDetails.controlling_faction_id)}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-blue-500" />
            <div>
              <p className="text-gray-400 text-sm">Capture Percentage</p>
              <p className="font-bold text-lg text-blue-400">
                {systemDetails.capture_percent.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <TrendingDown className="w-8 h-8 text-purple-500" />
            <div>
              <p className="text-gray-400 text-sm">Advantage Percentage</p>
              <p className="font-bold text-lg text-purple-400">
                {systemDetails.advantage_percent.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          {(() => {
            const frontlineInfo = getFrontlineClassificationInfo(systemDetails.frontline_classification)
            return (
              <div className="flex items-center gap-3">
                <div className="text-2xl">{frontlineInfo.icon}</div>
                <div>
                  <p className="text-gray-400 text-sm">Frontline Status</p>
                  <p className={`font-bold text-lg ${frontlineInfo.color}`}>
                    {frontlineInfo.label}
                  </p>
                </div>
              </div>
            )
          })()}
        </div>
      </div>

      {/* Time Range Selector */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">Historical Trends</h2>
          <div className="flex gap-2">
            {[6, 24, 72, 168].map((hours) => (
              <button
                key={hours}
                onClick={() => setTimeRange(hours)}
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  timeRange === hours
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {hours < 24 ? `${hours}h` : `${hours / 24}d`}
              </button>
            ))}
          </div>
        </div>

        {/* Chart */}
        {chartData.length > 0 ? (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="timestamp" 
                  stroke="#9CA3AF"
                  fontSize={12}
                />
                <YAxis 
                  stroke="#9CA3AF"
                  fontSize={12}
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
                  dot={{ fill: '#3B82F6', strokeWidth: 2, r: 3 }}
                />
                <Line 
                  type="monotone" 
                  dataKey="advantage_percent" 
                  stroke="#8B5CF6" 
                  strokeWidth={2}
                  name="Advantage %"
                  dot={{ fill: '#8B5CF6', strokeWidth: 2, r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-center py-8">
            <Calendar className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400">No historical data available for the selected time range.</p>
          </div>
        )}
      </div>

      {/* Recent Snapshots Table */}
      <div className="card">
        <h2 className="text-xl font-semibold text-white mb-6">Recent Snapshots</h2>
        {systemDetails.recent_snapshots.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4">Timestamp</th>
                  <th className="text-left py-3 px-4">Controlling Faction</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Capture %</th>
                  <th className="text-left py-3 px-4">Advantage %</th>
                </tr>
              </thead>
              <tbody>
                {systemDetails.recent_snapshots.map((snapshot, index) => (
                  <tr key={index} className="border-b border-gray-800">
                    <td className="py-3 px-4 text-gray-300">
                      {new Date(snapshot.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`font-medium ${getFactionColor(snapshot.controlling_faction_id)}`}>
                        {getFactionName(snapshot.controlling_faction_id)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {snapshot.contested ? (
                          <>
                            <AlertTriangle className="w-4 h-4 text-orange-500" />
                            <span className="text-orange-400">Contested</span>
                          </>
                        ) : (
                          <>
                            <Shield className="w-4 h-4 text-green-500" />
                            <span className="text-green-400">Stable</span>
                          </>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-700 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${Math.max(0, Math.min(100, snapshot.capture_percent))}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-300">
                          {snapshot.capture_percent.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-700 rounded-full h-2">
                          <div 
                            className={`${getAdvantageBarColor(snapshot)} h-2 rounded-full transition-all duration-300`}
                            style={{ width: `${Math.max(0, Math.min(100, snapshot.advantage_percent))}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-300">
                          {snapshot.advantage_percent.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <Clock className="w-12 h-12 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400">No recent snapshots available.</p>
          </div>
        )}
      </div>

      {/* Killmail Statistics */}
      {killmailStats && (
        <div className="card">
          <h2 className="text-xl font-semibold text-white mb-6">Most Active Killers (Last {killmailStats.time_window_hours}h)</h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Top Players */}
            <EntityList
              title="Top Players"
              icon={<Users className="w-6 h-6 text-blue-500" />}
              emptyMessage="No player data available"
            >
              {killmailStats.top_performers.players.slice(0, 10).map((player, index) => (
                <PlayerCard
                  key={player.character_id}
                  rank={index + 1}
                  characterId={player.character_id}
                  characterName={player.character_name}
                  kills={player.kills}
                  iskKilled={player.isk_killed}
                />
              ))}
            </EntityList>

            {/* Top Corporations */}
            <EntityList
              title="Top Corporations"
              icon={<Building className="w-6 h-6 text-purple-500" />}
              emptyMessage="No corporation data available"
            >
              {killmailStats.top_performers.corporations.slice(0, 10).map((corp, index) => (
                <CorporationCard
                  key={corp.corporation_id}
                  rank={index + 1}
                  corporationId={corp.corporation_id}
                  corporationName={corp.corporation_name}
                  ticker={corp.ticker}
                  kills={corp.kills}
                  iskKilled={corp.isk_killed}
                  uniquePlayers={corp.unique_players}
                />
              ))}
            </EntityList>

            {/* Top Alliances */}
            <EntityList
              title="Top Alliances"
              icon={<Crown className="w-6 h-6 text-yellow-500" />}
              emptyMessage="No alliance data available"
            >
              {killmailStats.top_performers.alliances.slice(0, 10).map((alliance, index) => (
                <AllianceCard
                  key={alliance.alliance_id}
                  rank={index + 1}
                  allianceId={alliance.alliance_id}
                  allianceName={alliance.alliance_name}
                  ticker={alliance.ticker}
                  kills={alliance.kills}
                  iskKilled={alliance.isk_killed}
                  uniquePlayers={alliance.unique_players}
                  uniqueCorporations={alliance.unique_corporations}
                />
              ))}
            </EntityList>
          </div>
          <div className="mt-4 text-center">
            <p className="text-gray-400 text-sm">
              Data generated at: {new Date(killmailStats.generated_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Staged Corporations */}
      {stagedCorporations && stagedCorporations.staged_corporations.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-white">
              Staged Corporations (Last {Math.floor(stagedCorporations.time_window_hours / 24)} days)
            </h2>
            <div className="flex items-center gap-2">
              <select
                value={stagingTimeRange}
                onChange={(e) => setStagingTimeRange(parseInt(e.target.value))}
                className="bg-gray-700 text-white px-3 py-1 rounded border border-gray-600 text-sm"
              >
                <option value={168}>7 days</option>
                <option value={336}>14 days</option>
                <option value={720}>30 days</option>
              </select>
            </div>
          </div>
          
          <div className="mb-4">
            <p className="text-gray-400 text-sm">
              Corporations that have their highest kill activity in this system. 
              These are likely using {systemDetails?.name} as their staging area.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4">Rank</th>
                  <th className="text-left py-3 px-4">Corporation</th>
                  <th className="text-left py-3 px-4">Alliance</th>
                  <th className="text-left py-3 px-4">Kills</th>
                  <th className="text-left py-3 px-4">ISK Destroyed</th>
                </tr>
              </thead>
              <tbody>
                {stagedCorporations.staged_corporations.map((corp, index) => (
                  <tr key={corp.corporation_id} className="border-b border-gray-800 hover:bg-gray-800/50">
                    <td className="py-3 px-4">
                      <span className="text-gray-300 font-medium">#{index + 1}</span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <EntityImage
                          src={getCorporationLogoUrl(corp.corporation_id, 64)}
                          fallbackSrc={getFallbackImageUrl('corporation')}
                          alt={`${corp.corporation_name} logo`}
                          className="w-10 h-10 flex-shrink-0"
                        />
                        <div className="flex flex-col">
                          <span className="text-white font-medium">{corp.corporation_name}</span>
                          <span className="text-gray-400 text-sm">[{corp.ticker}]</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {corp.alliance_name && corp.alliance_id ? (
                        <div className="flex items-center gap-3">
                          <EntityImage
                            src={getAllianceLogoUrl(corp.alliance_id, 64)}
                            fallbackSrc={getFallbackImageUrl('alliance')}
                            alt={`${corp.alliance_name} logo`}
                            className="w-10 h-10 flex-shrink-0"
                          />
                          <div className="flex flex-col">
                            <span className="text-purple-400 font-medium">{corp.alliance_name}</span>
                            <span className="text-gray-400 text-sm">[{corp.alliance_ticker}]</span>
                          </div>
                        </div>
                      ) : (
                        <span className="text-gray-500 italic">No Alliance</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="text-green-400 font-medium">{corp.kills}</span>
                        <span className="text-gray-400 text-sm">kills</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="text-yellow-400 font-medium">{formatISK(corp.isk_killed)}</span>
                        <span className="text-gray-400 text-sm">ISK</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 text-center">
            <p className="text-gray-400 text-sm">
              Showing {stagedCorporations.total_staged_corporations} corporation{stagedCorporations.total_staged_corporations !== 1 ? 's' : ''} staged in this system
            </p>
            <p className="text-gray-400 text-sm">
              Data generated at: {new Date(stagedCorporations.generated_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* System Information */}
      <div className="card">
        <h2 className="text-xl font-semibold text-white mb-6">System Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-gray-400 text-sm">System ID</p>
            <p className="text-white font-medium">{systemDetails.system_id}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Security Status</p>
            <p className="text-white font-medium">{systemDetails.security_status.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Created</p>
            <p className="text-white font-medium">
              {new Date(systemDetails.created_at).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Last Updated</p>
            <p className="text-white font-medium">
              {new Date(systemDetails.updated_at).toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
