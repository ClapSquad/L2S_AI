import styled from "styled-components";
import a from "./assets/Long2ShortTextHorizontal.png";
import Logo from "@components/Logo";
import NavigationBar from "@components/NavigationBar";

export default function MainPage() {
  return (
    <>
      <NavigationBar />
      <MainPageWrapper>
        <Logo size="20%" />
        <LargeText src={a} />
        <Heading>시간은 짧게, 인사이트는 깊게</Heading>
      </MainPageWrapper>
    </>
  );
}

const LargeText = styled.img`
  width: 30%;
`;

const Heading = styled.div`
  font-size: 30px;
  font-weight: bold;
`;

const MainPageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
`;
