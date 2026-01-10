import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { PackagesCacheProvider } from '@/lib/cache'
import { PackageList } from '@/pages/PackageList'
import { PackageDetail } from '@/pages/PackageDetail'

function App() {
  return (
    <PackagesCacheProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PackageList />} />
          <Route path="/packages/:name" element={<PackageDetail />} />
        </Routes>
      </BrowserRouter>
    </PackagesCacheProvider>
  )
}

export default App
