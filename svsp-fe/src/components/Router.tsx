import { Route, Routes } from "react-router-dom";
import MainPage from "@main/MainPage";
import LoginPage from "@login/LoginPage";
import RegisterPage from "@register/RegisterPage";
import MyPage from "@my/MyPage";

export default function Router() {
  return (
    <Routes>
      <Route path="/" element={<MainPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/my" element={<MyPage />} />
    </Routes>
  );
}
