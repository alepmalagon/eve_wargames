import React, { useState } from 'react'
import { Users, Building, Crown } from 'lucide-react'
import { 
  getCharacterPortraitUrl, 
  getCorporationLogoUrl, 
  getAllianceLogoUrl, 
  getFallbackImageUrl 
} from '../utils/eveImages'

interface BaseEntityProps {
  rank: number
  kills: number
  iskKilled: number
}

interface PlayerCardProps extends BaseEntityProps {
  characterId: number
  characterName: string
}

interface CorporationCardProps extends BaseEntityProps {
  corporationId: number
  corporationName: string
  ticker: string
  uniquePlayers: number
}

interface AllianceCardProps extends BaseEntityProps {
  allianceId: number
  allianceName: string
  ticker: string
  uniquePlayers: number
  uniqueCorporations: number
}

const formatISK = (value: number) => {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toFixed(0)
}

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

export const PlayerCard: React.FC<PlayerCardProps> = ({
  rank,
  characterId,
  characterName,
  kills,
  iskKilled
}) => {
  const portraitUrl = getCharacterPortraitUrl(characterId, 64)
  const fallbackUrl = getFallbackImageUrl('character')

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
      <div className="flex items-center gap-3 flex-1">
        <span className="text-gray-400 font-medium text-sm w-6 text-center">#{rank}</span>
        <EntityImage
          src={portraitUrl}
          fallbackSrc={fallbackUrl}
          alt={`${characterName} portrait`}
          className="w-10 h-10 flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate">{characterName}</p>
          <div className="flex gap-4 text-sm">
            <span className="text-red-400">{kills} kills</span>
            <span className="text-green-400">{formatISK(iskKilled)} ISK</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export const CorporationCard: React.FC<CorporationCardProps> = ({
  rank,
  corporationId,
  corporationName,
  ticker,
  kills,
  iskKilled,
  uniquePlayers
}) => {
  const logoUrl = getCorporationLogoUrl(corporationId, 64)
  const fallbackUrl = getFallbackImageUrl('corporation')

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
      <div className="flex items-center gap-3 flex-1">
        <span className="text-gray-400 font-medium text-sm w-6 text-center">#{rank}</span>
        <EntityImage
          src={logoUrl}
          fallbackSrc={fallbackUrl}
          alt={`${corporationName} logo`}
          className="w-10 h-10 flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate">
            [{ticker}] {corporationName}
          </p>
          <div className="flex gap-4 text-sm">
            <span className="text-red-400">{kills} kills</span>
            <span className="text-green-400">{formatISK(iskKilled)} ISK</span>
            <span className="text-blue-400">{uniquePlayers} pilots</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export const AllianceCard: React.FC<AllianceCardProps> = ({
  rank,
  allianceId,
  allianceName,
  ticker,
  kills,
  iskKilled,
  uniquePlayers,
  uniqueCorporations
}) => {
  const logoUrl = getAllianceLogoUrl(allianceId, 64)
  const fallbackUrl = getFallbackImageUrl('alliance')

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors">
      <div className="flex items-center gap-3 flex-1">
        <span className="text-gray-400 font-medium text-sm w-6 text-center">#{rank}</span>
        <EntityImage
          src={logoUrl}
          fallbackSrc={fallbackUrl}
          alt={`${allianceName} logo`}
          className="w-10 h-10 flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate">
            &lt;{ticker}&gt; {allianceName}
          </p>
          <div className="flex gap-4 text-sm">
            <span className="text-red-400">{kills} kills</span>
            <span className="text-green-400">{formatISK(iskKilled)} ISK</span>
            <span className="text-blue-400">{uniquePlayers} pilots</span>
            <span className="text-purple-400">{uniqueCorporations} corps</span>
          </div>
        </div>
      </div>
    </div>
  )
}

interface EntityListProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  emptyMessage?: string
}

export const EntityList: React.FC<EntityListProps> = ({
  title,
  icon,
  children,
  emptyMessage = "No data available"
}) => {
  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <div className="flex items-center gap-3 mb-4">
        {icon}
        <h3 className="text-lg font-semibold text-white">{title}</h3>
      </div>
      <div className="space-y-2">
        {children || (
          <p className="text-gray-400 text-center py-4">{emptyMessage}</p>
        )}
      </div>
    </div>
  )
}
