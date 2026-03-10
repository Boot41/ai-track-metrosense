import { Navigate, Route, Routes } from "react-router-dom";
import ChatPage from "@/pages/ChatPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
