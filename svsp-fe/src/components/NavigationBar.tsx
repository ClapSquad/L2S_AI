import routePath from "@router/routePath";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { LoginIcon } from "src/icons/LoginIcon";
import { globalButtonStyle } from "@styles/globalStyle";
import Logo from "./Logo";
import { SettingsIcon } from "src/icons/SettingsIcon";
import { Modal } from "./Modal";
import { useModal } from "@hooks/useModal";
import SettingModal from "./SettingModal";

export default function NavigationBar() {
  const navigate = useNavigate();
  const { isOpen, open, close } = useModal();

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
          <Button onClick={() => navigate(routePath.LOGIN)}>
            <LoginIcon size="30" color="black" />
          </Button>
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
`;
