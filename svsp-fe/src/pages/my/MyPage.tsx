import React, { useState } from "react";
import FileUpload from "../../components/FileUpload";

const MyPage: React.FC = () => {
  const [user, setUser] = useState({
    email: "user@example.com",
    name: "홍길동",
  });

  const handleDelete = () => {
    if (window.confirm("정말 탈퇴하시겠습니까?")) {
      alert("회원 탈퇴 완료");
    }
  };

  return (
    <div>
      <h2>마이페이지</h2>
      <p>이메일: {user.email}</p>
      <p>이름: {user.name}</p>
      <button onClick={() => alert("수정 기능은 아직 미구현입니다.")}>
        회원 정보 수정
      </button>
      <button onClick={handleDelete} style={{ marginLeft: "10px" }}>
        회원 탈퇴
      </button>

      <hr />
      <FileUpload />
    </div>
  );
};

export default MyPage;
