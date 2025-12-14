import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Navigation } from './components/Navigation'
import { Dashboard } from './components/Dashboard'
import { SystemsView } from './components/SystemsView'
import { KillsView } from './components/KillsView'

function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Navigation />
      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/systems" element={<SystemsView />} />
          <Route path="/kills" element={<KillsView />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
