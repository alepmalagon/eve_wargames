import React, { useState, useEffect } from 'react'
import { Trophy, Target } from 'lucide-react'

interface LeaderboardPlayer {
  id: number
  name: string
  kills: {
    yesterday: number
    lastWeek: number
    total: number
  }
  victoryPoints: {
    yesterday: number
    lastWeek: number
    total: number
  }
  currentRank: number
  faction: {
    id: number
  }
  corporation?: {
    id: number
    name: string
  }
  alliance?: {
    id: number
    name: string
  }
}

interface LeaderboardData {
  [factionId: string]: {
    killsLastWeek: LeaderboardPlayer[]
    pointsLastWeek: LeaderboardPlayer[]
  }
}

const formatISK = (value: number) => {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toFixed(0)
}

const getCharacterPortraitUrl = (characterId: number, size: number = 64) => {
  return `https://images.evetech.net/characters/${characterId}/portrait?size=${size}`
}

interface PlayerCardProps {
  player: LeaderboardPlayer
  rank: number
  factionColor: string
}

const PlayerCard: React.FC<PlayerCardProps> = ({ player, rank, factionColor }) => {
  const [imageError, setImageError] = useState(false)
  const [imageLoading, setImageLoading] = useState(true)

  const handleImageLoad = () => {
    setImageLoading(false)
  }

  const handleImageError = () => {
    setImageError(true)
    setImageLoading(false)
  }

  const portraitUrl = getCharacterPortraitUrl(player.id, 64)
  const fallbackUrl = 'https://images.evetech.net/characters/1/portrait?size=64'

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
      <div className="flex items-center gap-3 flex-1">
        <span className="text-gray-400 font-medium text-sm w-6 text-center">#{rank}</span>
        <div className="relative w-10 h-10 flex-shrink-0">
          {imageLoading && (
            <div className="absolute inset-0 bg-gray-700 animate-pulse rounded-full"></div>
          )}
          <img
            src={imageError ? fallbackUrl : portraitUrl}
            alt={`${player.name} portrait`}
            className={`w-full h-full object-cover rounded-full ${imageLoading ? 'opacity-0' : 'opacity-100'} transition-opacity duration-200`}
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate">{player.name}</p>
          <div className="flex gap-4 text-sm">
            <span className="text-red-400">{player.kills.lastWeek} kills</span>
            <span className={factionColor}>{formatISK(player.victoryPoints.total)} VP</span>
          </div>
        </div>
      </div>
    </div>
  )
}

interface LeaderboardSectionProps {
  title: string
  players: LeaderboardPlayer[]
  factionColor: string
  icon: React.ReactNode
}

const LeaderboardSection: React.FC<LeaderboardSectionProps> = ({ 
  title, 
  players, 
  factionColor, 
  icon 
}) => {
  const topPlayers = players.slice(0, 5) // Show top 5 players

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <div className="flex items-center gap-3 mb-4">
        {icon}
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      <div className="space-y-2">
        {topPlayers.length > 0 ? (
          topPlayers.map((player, index) => (
            <PlayerCard
              key={player.id}
              player={player}
              rank={index + 1}
              factionColor={factionColor}
            />
          ))
        ) : (
          <p className="text-gray-400 text-center py-4">No data available</p>
        )}
      </div>
    </div>
  )
}

export const LeaderboardCards: React.FC = () => {
  const [leaderboardData, setLeaderboardData] = useState<LeaderboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Use useRef to track if we've already fetched data and to store the interval
  const hasFetchedRef = React.useRef(false)
  const intervalRef = React.useRef<NodeJS.Timeout | null>(null)
  const lastFetchTimeRef = React.useRef<number>(0)

  useEffect(() => {
    const fetchLeaderboardData = async (force: boolean = false) => {
      // Prevent unnecessary fetches - only fetch if:
      // 1. We haven't fetched before, OR
      // 2. It's been more than 10 minutes since last fetch, OR
      // 3. Force refresh is requested
      const now = Date.now()
      const timeSinceLastFetch = now - lastFetchTimeRef.current
      const tenMinutes = 10 * 60 * 1000
      
      if (!force && hasFetchedRef.current && timeSinceLastFetch < tenMinutes) {
        return
      }

      try {
        setLoading(true)
        // Use the backend proxy endpoint to avoid CORS issues
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/v1/faction-warfare/leaderboard`)
        
        if (!response.ok) {
          throw new Error('Failed to fetch leaderboard data')
        }
        
        const data = await response.json()
        setLeaderboardData(data)
        setError(null)
        hasFetchedRef.current = true
        lastFetchTimeRef.current = now
      } catch (err) {
        setError('Failed to fetch leaderboard data')
        console.error('Error fetching leaderboard:', err)
      } finally {
        setLoading(false)
      }
    }

    // Only fetch if we haven't fetched before
    if (!hasFetchedRef.current) {
      fetchLeaderboardData()
    }
    
    // Clear any existing interval to prevent duplicates
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    
    // Set up interval for automatic refresh every 10 minutes
    intervalRef.current = setInterval(() => {
      fetchLeaderboardData(true) // Force refresh on interval
    }, 10 * 60 * 1000)
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, []) // Empty dependency array is correct here

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="text-lg text-gray-400">Loading leaderboard data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="text-lg text-red-400">{error}</div>
      </div>
    )
  }

  if (!leaderboardData) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="text-lg text-gray-400">No leaderboard data available</div>
      </div>
    )
  }

  // Extract Minmatar (500002) and Amarr (500001) data
  const minmatarData = leaderboardData['500002']
  const amarrData = leaderboardData['500001']

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white mb-2">
          Faction Warfare Leaderboards
        </h2>
        <p className="text-gray-400">
          Top pilots by kills and victory points
        </p>
      </div>

      {/* Minmatar Leaderboards */}
      {minmatarData && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold text-red-400 flex items-center gap-2">
            <span>🔴</span> Minmatar Republic
          </h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <LeaderboardSection
              title="Top Killers (Last Week)"
              players={minmatarData.killsLastWeek || []}
              factionColor="text-red-400"
              icon={<Target className="text-red-400" size={20} />}
            />
            <LeaderboardSection
              title="Top Victory Points (Last Week)"
              players={minmatarData.pointsLastWeek || []}
              factionColor="text-red-400"
              icon={<Trophy className="text-red-400" size={20} />}
            />
          </div>
        </div>
      )}

      {/* Amarr Leaderboards */}
      {amarrData && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold text-yellow-400 flex items-center gap-2">
            <span>🟡</span> Amarr Empire
          </h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <LeaderboardSection
              title="Top Killers (Last Week)"
              players={amarrData.killsLastWeek || []}
              factionColor="text-yellow-400"
              icon={<Target className="text-yellow-400" size={20} />}
            />
            <LeaderboardSection
              title="Top Victory Points (Last Week)"
              players={amarrData.pointsLastWeek || []}
              factionColor="text-yellow-400"
              icon={<Trophy className="text-yellow-400" size={20} />}
            />
          </div>
        </div>
      )}
    </div>
  )
}
