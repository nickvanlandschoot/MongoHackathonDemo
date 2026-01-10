import { BrowserRouter, Routes, Route } from 'react-router-dom'

function HomePage() {
  return (
    <div className="min-h-screen bg-neutral-950">
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
