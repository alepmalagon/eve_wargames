import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Map, Zap } from 'lucide-react'
import clsx from 'clsx'

export const Navigation: React.FC = () => {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/systems', label: 'Systems', icon: Map },
    { path: '/kills', label: 'Kills', icon: Zap },
  ]

  return (
    <nav className="bg-gray-800 border-b border-gray-700">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link to="/" className="text-xl font-bold text-white">
              EVE Wargames
            </Link>
            <div className="flex space-x-4">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={clsx(
                    'flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                    location.pathname === path
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  )}
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </Link>
              ))}
            </div>
          </div>
          <div className="text-sm text-gray-400">
            Minmatar vs Amarr Warzone
          </div>
        </div>
      </div>
    </nav>
  )
}
