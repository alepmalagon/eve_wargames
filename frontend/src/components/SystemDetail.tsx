import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { systemsApi } from '../services/api'
import { 
  ArrowLeft, 
  AlertTriangle, 
  Shield, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  RefreshCw,
  Calendar
} from 'lucide-react'
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
  created_at: string
  updated_at: string
  recent_snapshots: Array<{
    timestamp: string
    controlling_faction_id: number
    contested: boolean
    capture_percent: number
    advantage_percent: number
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
  }>
}

export const SystemDetail: React.FC = () => {
  const { systemId } = useParams<{ systemId: string }>()
  const navigate = useNavigate()
  const [systemDetails, setSystemDetails] = useState<SystemDetails | null>(null)
  const [trendData, setTrendData] = useState<TrendData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState(24)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (systemId) {
      fetchSystemData()
    }
  }, [systemId, timeRange])

  const fetchSystemData = async () => {
    if (!systemId) return

    try {
      setLoading(true)
      setError(null)

      const [detailsResponse, trendsResponse] = await Promise.all([
        systemsApi.getSystemDetails(parseInt(systemId)),
        systemsApi.getSystemTrends(parseInt(systemId), timeRange)
      ])

      setSystemDetails(detailsResponse.data)
      setTrendData(trendsResponse.data)
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

  const getFactionColor = (factionId: number) => {
    switch (factionId) {
      case 500002: return 'text-minmatar-red'
      case 500003: return 'text-amarr-yellow'
      default: return 'text-gray-400'
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
                            className="bg-purple-500 h-2 rounded-full"
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
