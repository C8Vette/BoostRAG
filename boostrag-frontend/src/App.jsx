import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import Landing from "./pages/Landing";
import Research from "./pages/Research";
import CategoryPage from "./pages/CategoryPage";
import Login from "./pages/Login";
import Garage from "./pages/Garage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/research" element={<Research />} />
          <Route path="/login" element={<Login />} />
          <Route path="/garage" element={<Garage />} />
          <Route path="/category/:slug" element={<CategoryPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
