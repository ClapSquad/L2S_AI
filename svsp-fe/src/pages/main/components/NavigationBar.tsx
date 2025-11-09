import routePath from "@router/routePath";
import { useNavigate } from "react-router-dom";
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

export default function NavigationBar() {
  const navigate = useNavigate();
  const { isOpen, open, close } = useModal();
  const isLoggedIn = useIsLoggedIn();
  const { mutate } = useLogout();

  return (
    <>
      <Modal isOpen={isOpen} onClose={close}>
        <SettingModal onClose={close} />
      </Modal>
      <NavigationBarWrapper>
        <Button onClick={() => navigate(routePath.HOME)}>
          <Logo size="40px" />
        </Button>
        <ButtonSet>
          {isLoggedIn ? (
            <>
              <Button onClick={() => mutate()}>
                <LogoutIcon size="30" color="black" />
              </Button>
              <Button onClick={() => navigate(routePath.MY)}>
                <AccountCircleIcon size="30" color="black" />
              </Button>
            </>
          ) : (
            <Button onClick={() => navigate(routePath.LOGIN)}>
              <LoginIcon size="30" color="black" />
            </Button>
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
