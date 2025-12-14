import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { systemsApi } from '../services/api'
import { ChevronUp, ChevronDown, Filter, Search, AlertTriangle, Shield } from 'lucide-react'

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
}

type SortField = 'name' | 'controlling_faction_id' | 'capture_percent' | 'advantage_percent' | 'updated_at'
type SortDirection = 'asc' | 'desc'

export const SystemsView: React.FC = () => {
  const navigate = useNavigate()
  const [systems, setSystems] = useState<System[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [factionFilter, setFactionFilter] = useState<number | null>(null)
  const [contestedFilter, setContestedFilter] = useState<boolean | null>(null)
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  // Faction constants
  const MINMATAR_FACTION_ID = 500002
  const AMARR_FACTION_ID = 500003

  // Function to get advantage bar color based on leading faction
  const getAdvantageBarColor = (system: System) => {
    // Debug logging to see what values we're getting
    console.log(`System ${system.name}: Minmatar=${system.minmatar_advantage}, Amarr=${system.amarr_advantage}`)
    
    if (system.minmatar_advantage > system.amarr_advantage) {
      return 'bg-red-400' // Minmatar color - rgb(248 113 113)
    } else if (system.amarr_advantage > system.minmatar_advantage) {
      return 'bg-yellow-400' // Amarr color - rgb(250 204 21)
    } else {
      return 'bg-gray-500' // Neutral/equal
    }
  }

  useEffect(() => {
    fetchSystems()
  }, [factionFilter, contestedFilter])

  const fetchSystems = async () => {
    try {
      setLoading(true)
      const response = await systemsApi.getSystems(
        factionFilter || undefined,
        contestedFilter || undefined
      )
      setSystems(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to fetch systems data')
      console.error('Error fetching systems:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
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

  const filteredAndSortedSystems = systems
    .filter(system => 
      system.name.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      let aValue: any = a[sortField]
      let bValue: any = b[sortField]
      
      if (sortField === 'updated_at') {
        aValue = new Date(aValue).getTime()
        bValue = new Date(bValue).getTime()
      }
      
      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase()
        bValue = bValue.toLowerCase()
      }
      
      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
      return 0
    })

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ChevronUp className="w-4 h-4 opacity-30" />
    return sortDirection === 'asc' ? 
      <ChevronUp className="w-4 h-4" /> : 
      <ChevronDown className="w-4 h-4" />
  }

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">System Control</h1>
          <p className="text-gray-400">Loading systems data...</p>
        </div>
        <div className="card">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-700 rounded w-1/4"></div>
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">System Control</h1>
          <p className="text-gray-400">Monitor system capture percentages and control status</p>
        </div>
        <div className="card">
          <div className="text-center py-8">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-400 mb-4">{error}</p>
            <button 
              onClick={fetchSystems}
              className="btn btn-primary"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-2">
          System Control
        </h1>
        <p className="text-gray-400">
          Monitor system capture percentages and control status
        </p>
      </div>

      {/* Filters and Search */}
      <div className="card">
        <div className="flex flex-col lg:flex-row gap-4 mb-6">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search systems..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Faction Filter */}
          <div className="flex gap-2">
            <button
              onClick={() => setFactionFilter(null)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                factionFilter === null 
                  ? 'bg-blue-600 border-blue-500 text-white' 
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
              }`}
            >
              All Factions
            </button>
            <button
              onClick={() => setFactionFilter(500002)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                factionFilter === 500002 
                  ? 'bg-minmatar-red border-minmatar-red text-white' 
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Minmatar
            </button>
            <button
              onClick={() => setFactionFilter(500003)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                factionFilter === 500003 
                  ? 'bg-amarr-yellow border-amarr-yellow text-black' 
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Amarr
            </button>
          </div>

          {/* Contested Filter */}
          <div className="flex gap-2">
            <button
              onClick={() => setContestedFilter(null)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                contestedFilter === null 
                  ? 'bg-blue-600 border-blue-500 text-white' 
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
              }`}
            >
              All Systems
            </button>
            <button
              onClick={() => setContestedFilter(true)}
              className={`px-4 py-2 rounded-lg border transition-colors ${
                contestedFilter === true 
                  ? 'bg-orange-600 border-orange-500 text-white' 
                  : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Contested Only
            </button>
          </div>
        </div>

        {/* Systems Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700">
                <th 
                  className="text-left py-3 px-4 cursor-pointer hover:bg-gray-800 transition-colors"
                  onClick={() => handleSort('name')}
                >
                  <div className="flex items-center gap-2">
                    System Name
                    <SortIcon field="name" />
                  </div>
                </th>
                <th 
                  className="text-left py-3 px-4 cursor-pointer hover:bg-gray-800 transition-colors"
                  onClick={() => handleSort('controlling_faction_id')}
                >
                  <div className="flex items-center gap-2">
                    Controlling Faction
                    <SortIcon field="controlling_faction_id" />
                  </div>
                </th>
                <th className="text-left py-3 px-4">Status</th>
                <th 
                  className="text-left py-3 px-4 cursor-pointer hover:bg-gray-800 transition-colors"
                  onClick={() => handleSort('capture_percent')}
                >
                  <div className="flex items-center gap-2">
                    Capture %
                    <SortIcon field="capture_percent" />
                  </div>
                </th>
                <th 
                  className="text-left py-3 px-4 cursor-pointer hover:bg-gray-800 transition-colors"
                  onClick={() => handleSort('advantage_percent')}
                >
                  <div className="flex items-center gap-2">
                    Advantage %
                    <SortIcon field="advantage_percent" />
                  </div>
                </th>
                <th 
                  className="text-left py-3 px-4 cursor-pointer hover:bg-gray-800 transition-colors"
                  onClick={() => handleSort('updated_at')}
                >
                  <div className="flex items-center gap-2">
                    Last Updated
                    <SortIcon field="updated_at" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedSystems.map((system) => (
                <tr 
                  key={system.system_id}
                  className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer transition-colors"
                  onClick={() => navigate(`/systems/${system.system_id}`)}
                >
                  <td className="py-3 px-4">
                    <div className="font-medium text-white">{system.name}</div>
                    <div className="text-sm text-gray-400">ID: {system.system_id}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`font-medium ${getFactionColor(system.controlling_faction_id)}`}>
                      {getFactionName(system.controlling_faction_id)}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      {system.contested ? (
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
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${Math.max(0, Math.min(100, system.capture_percent))}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-300 w-12">
                        {system.capture_percent.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-700 rounded-full h-2">
                        <div 
                          className={`${getAdvantageBarColor(system)} h-2 rounded-full transition-all duration-300`}
                          style={{ width: `${Math.max(0, Math.min(100, system.advantage_percent))}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-300 w-12">
                        {system.advantage_percent.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-gray-400 text-sm">
                    {new Date(system.updated_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredAndSortedSystems.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-400">No systems found matching your criteria.</p>
          </div>
        )}

        <div className="mt-4 text-sm text-gray-400">
          Showing {filteredAndSortedSystems.length} of {systems.length} systems
        </div>
      </div>
    </div>
  )
}
