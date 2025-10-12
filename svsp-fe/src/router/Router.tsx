import { Route, Routes } from "react-router-dom";
import MainPage from "@main/MainPage";
import LoginPage from "@login/LoginPage";
import RegisterPage from "@register/RegisterPage";
import MyPage from "@my/MyPage";
import routePath from "./routePath";

export default function Router() {
  return (
    <Routes>
      <Route path={routePath.HOME} element={<MainPage />} />
      <Route path={routePath.LOGIN} element={<LoginPage />} />
      <Route path={routePath.REGISTER} element={<RegisterPage />} />
      <Route path={routePath.MY} element={<MyPage />} />
    </Routes>
  );
}
