import routePath from "@router/routePath";
import { Link } from "react-router-dom";

export default function NavigationBar() {
  return (
    <nav style={{ marginBottom: "20px" }}>
      <Link to={routePath.HOME} style={{ marginRight: "10px" }}>
        홈페이지
      </Link>
      <Link to={routePath.LOGIN} style={{ marginRight: "10px" }}>
        로그인
      </Link>
      <Link to={routePath.REGISTER} style={{ marginRight: "10px" }}>
        회원가입
      </Link>
      <Link to={routePath.MY}>마이페이지</Link>
    </nav>
  );
}
