import { Link } from "react-router-dom";

export default function NavigationBar() {
  return (
    <nav style={{ marginBottom: "20px" }}>
      <Link to="/" style={{ marginRight: "10px" }}>
        홈페이지
      </Link>
      <Link to="/login" style={{ marginRight: "10px" }}>
        로그인
      </Link>
      <Link to="/register" style={{ marginRight: "10px" }}>
        회원가입
      </Link>
      <Link to="/my">마이페이지</Link>
    </nav>
  );
}
