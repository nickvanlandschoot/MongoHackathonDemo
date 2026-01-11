import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { PackagesCacheProvider, AlertsCacheProvider, PackageDetailCacheProvider } from '@/lib/cache'
import { PackageList } from '@/pages/PackageList'
import { PackageDetail } from '@/pages/PackageDetail'
import { AlertsDashboard } from '@/pages/AlertsDashboard'

function App() {
  return (
    <PackagesCacheProvider>
      <AlertsCacheProvider>
        <PackageDetailCacheProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<PackageList />} />
              {/* Use wildcard to capture scoped npm packages like @scope/package */}
              <Route path="/packages/*" element={<PackageDetail />} />
              <Route path="/alerts" element={<AlertsDashboard />} />
            </Routes>
          </BrowserRouter>
        </PackageDetailCacheProvider>
      </AlertsCacheProvider>
    </PackagesCacheProvider>
  )
}

export default App
