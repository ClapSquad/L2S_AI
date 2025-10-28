import routePath from "@router/routePath";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { LoginIcon } from "src/icons/LoginIcon";
import { globalButtonStyle } from "@styles/globalStyle";
import Logo from "./Logo";

export default function NavigationBar() {
  const navigate = useNavigate();
  return (
    <NavigationBarWrapper>
      <HomeButton onClick={() => navigate(routePath.HOME)}>
        <Logo size="40px" />
      </HomeButton>
      <ButtonSet>
        <LoginButton onClick={() => navigate(routePath.LOGIN)}>
          <LoginIcon size="30" color="black" />
        </LoginButton>
      </ButtonSet>
    </NavigationBarWrapper>
  );
}

const HomeButton = styled.button`
  ${globalButtonStyle}
  padding: 10px;
`;

const LoginButton = styled.button`
  ${globalButtonStyle}
`;

const ButtonSet = styled.div`
  display: flex;

  padding: 4px;
`;

const NavigationBarWrapper = styled.nav`
  display: flex;

  justify-content: space-between;
  align-items: center;
`;
