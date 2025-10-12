import { Route, Routes } from "react-router-dom";
import LoginPage from "../pages/login/LoginPage";
import RegisterPage from "../pages/register/RegisterPage";
import MyPage from "../pages/my/MyPage";

export default function Router() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/mypage" element={<MyPage />} />
    </Routes>
  );
}
