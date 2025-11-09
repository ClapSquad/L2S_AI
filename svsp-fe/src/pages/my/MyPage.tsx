import { useContext } from "react";
import FileUpload from "../../components/FileUpload";
import { AuthContext } from "src/contexts/AuthContext";
import { toast } from "react-toastify";
import { useNavigateBack } from "@hooks/userNavigateBack";
import styled from "styled-components";
import NavigationBar from "@components/NavigationBar";

export default function MyPage() {
  const { user } = useContext(AuthContext);
  const navigateBack = useNavigateBack();

  if (!user) {
    toast.info("로그인이 필요합니다.");
    navigateBack();
    return;
  }

  return (
    <>
      <NavigationBar />
      <MyPageWrapper>
        <h2>마이페이지</h2>
        <p>이메일: {user.email}</p>
        <p>이름: {user.username}</p>
        <button onClick={() => toast.error("수정 기능은 아직 미구현입니다.")}>
          회원 정보 수정
        </button>
        <button onClick={() => toast.error("탈퇴 기능은 아직 미구현입니다.")}>
          회원 탈퇴
        </button>

        <hr />
        <FileUpload />
      </MyPageWrapper>
    </>
  );
}

const MyPageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
`;
