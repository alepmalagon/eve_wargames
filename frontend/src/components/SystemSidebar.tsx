import React from 'react'
import { Shield, AlertTriangle, Clock, Users } from 'lucide-react'

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

interface SystemSidebarProps {
  selectedSystem: System | null
  onClose: () => void
}

export const SystemSidebar: React.FC<SystemSidebarProps> = ({ selectedSystem, onClose }) => {
  if (!selectedSystem) {
    return (
      <div className="w-80 bg-gray-900 border-l border-gray-700 p-6 flex items-center justify-center">
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
    <div className="w-80 bg-gray-900 border-l border-gray-700 p-6 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-white">System Details</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors"
        >
          ×
        </button>
      </div>

      {/* System Name */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-2">{selectedSystem.name}</h2>
        <div className="flex items-center gap-4 text-sm text-gray-400">
          <span>ID: {selectedSystem.system_id}</span>
          <span className={getSecurityColor(selectedSystem.security_status)}>
            Sec: {selectedSystem.security_status.toFixed(1)}
          </span>
        </div>
      </div>

      {/* Status */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          {selectedSystem.contested ? (
            <>
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              <span className="text-orange-400 font-medium">Contested</span>
            </>
          ) : (
            <>
              <Shield className="w-5 h-5 text-green-500" />
              <span className="text-green-400 font-medium">Stable</span>
            </>
          )}
        </div>
      </div>

      {/* Controlling Faction */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Controlling Faction</h4>
        <div className={`text-lg font-semibold ${getFactionColor(selectedSystem.controlling_faction_id)}`}>
          {getFactionName(selectedSystem.controlling_faction_id)}
        </div>
      </div>

      {/* Frontline Classification */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Frontline Classification</h4>
        {(() => {
          const frontlineInfo = getFrontlineClassificationInfo(selectedSystem.frontline_classification, selectedSystem.controlling_faction_id)
          return (
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="text-lg">{frontlineInfo.icon}</span>
                <span className={`font-semibold px-3 py-1 rounded-full ${frontlineInfo.bgColor} ${frontlineInfo.color}`}>
                  {frontlineInfo.label}
                </span>
              </div>
              <p className="text-sm text-gray-400">{frontlineInfo.description}</p>
            </div>
          )
        })()}
      </div>

      {/* Capture Progress */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Capture Progress</h4>
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-gray-700 rounded-full h-3">
            <div 
              className="bg-blue-500 h-3 rounded-full transition-all duration-300"
              style={{ width: `${Math.max(0, Math.min(100, selectedSystem.capture_percent))}%` }}
            ></div>
          </div>
          <span className="text-sm text-gray-300 w-12">
            {selectedSystem.capture_percent.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Advantage */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Faction Advantage</h4>
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-gray-700 rounded-full h-3">
            <div 
              className={`${getAdvantageBarColor(selectedSystem)} h-3 rounded-full transition-all duration-300`}
              style={{ width: `${Math.max(0, Math.min(100, selectedSystem.advantage_percent))}%` }}
            ></div>
          </div>
          <span className="text-sm text-gray-300 w-12">
            {selectedSystem.advantage_percent.toFixed(1)}%
          </span>
        </div>
        
        {/* Detailed advantage breakdown */}
        <div className="mt-3 space-y-2">
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
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Last Updated</h4>
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Clock className="w-4 h-4" />
          <span>{new Date(selectedSystem.updated_at).toLocaleString()}</span>
        </div>
      </div>

      {/* Additional Actions */}
      <div className="border-t border-gray-700 pt-4">
        <button
          onClick={() => window.open(`/systems/${selectedSystem.system_id}`, '_blank')}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg transition-colors"
        >
          View Detailed Stats
        </button>
      </div>
    </div>
  )
}
