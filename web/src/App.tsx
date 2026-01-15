import { Routes, Route, Link } from 'react-router-dom'
import { FileText, Home, Settings } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import DocumentView from './pages/DocumentView'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center px-2 text-gray-900">
                <span className="text-xl font-bold text-geo-600">geo-lm</span>
              </Link>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/"
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 border-b-2 border-geo-500"
                >
                  <Home className="w-4 h-4 mr-2" />
                  Dashboard
                </Link>
              </div>
            </div>
            <div className="flex items-center">
              <button className="p-2 text-gray-400 hover:text-gray-500">
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/documents/:id" element={<DocumentView />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
