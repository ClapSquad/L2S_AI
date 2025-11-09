import routePath from "@router/routePath";
import { useLocation, useNavigate } from "react-router-dom";
import styled from "styled-components";
import { LoginIcon } from "src/icons/LoginIcon";
import { globalButtonStyle } from "@styles/globalStyle";
import { SettingsIcon } from "src/icons/SettingsIcon";
import { useModal } from "@hooks/useModal";
import { Modal } from "@components/Modal";
import SettingModal from "@components/SettingModal";
import Logo from "@components/Logo";
import { useIsLoggedIn } from "@hooks/useIsLoggedIn";
import { LogoutIcon } from "src/icons/LogoutIcon";
import { AccountCircleIcon } from "src/icons/AccountCircleIcon";
import { useLogout } from "@apis/hooks/useLogout";
import { useNavigateBack } from "@hooks/userNavigateBack";
import { ArrowBackIcon } from "src/icons/ArrowBackIcon";

export default function NavigationBar() {
  const navigateBack = useNavigateBack();
  const navigate = useNavigate();
  const { isOpen, open, close } = useModal();
  const isLoggedIn = useIsLoggedIn();
  const { mutate } = useLogout();
  const location = useLocation();
  const isMyPage = location.pathname === routePath.MY;
  const isAuthPage =
    location.pathname === routePath.LOGIN ||
    location.pathname === routePath.REGISTER;
  const isHomePage = location.pathname === routePath.HOME;
  return (
    <>
      <Modal isOpen={isOpen} onClose={close}>
        <SettingModal onClose={close} />
      </Modal>
      <NavigationBarWrapper>
        {isHomePage ? (
          <Button onClick={() => navigate(routePath.HOME)}>
            <Logo size="40px" />
          </Button>
        ) : (
          <Button onClick={() => navigateBack()}>
            <ArrowBackIcon size="30" color="black" />
          </Button>
        )}

        <ButtonSet>
          {isLoggedIn ? (
            <>
              <Button onClick={() => mutate()}>
                <LogoutIcon size="30" color="black" />
              </Button>
              {!isMyPage && (
                <Button onClick={() => navigate(routePath.MY)}>
                  <AccountCircleIcon size="30" color="black" />
                </Button>
              )}
            </>
          ) : (
            !isAuthPage && (
              <Button onClick={() => navigate(routePath.LOGIN)}>
                <LoginIcon size="30" color="black" />
              </Button>
            )
          )}
          <Button onClick={open}>
            <SettingsIcon size="30" color="black" />
          </Button>
        </ButtonSet>
      </NavigationBarWrapper>
    </>
  );
}

const Button = styled.button`
  ${globalButtonStyle}
`;

const ButtonSet = styled.div`
  display: flex;
  gap: 8px;
`;

const NavigationBarWrapper = styled.nav`
  display: flex;

  justify-content: space-between;
  align-items: center;

  padding: 8px;
  height: 40px;
`;
