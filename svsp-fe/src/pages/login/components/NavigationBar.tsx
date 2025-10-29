import routePath from "@router/routePath";
import { useNavigate } from "react-router-dom";
import styled from "styled-components";
import { globalButtonStyle } from "@styles/globalStyle";
import { SettingsIcon } from "src/icons/SettingsIcon";
import { useModal } from "@hooks/useModal";
import { Modal } from "@components/Modal";
import SettingModal from "@components/SettingModal";
import { ArrowBackIcon } from "src/icons/ArrowBackIcon";

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
          <ArrowBackIcon size="30" color="black" />
        </Button>
        <ButtonSet>
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
  align-self: normal;
  display: flex;

  justify-content: space-between;
  align-items: center;

  padding: 8px;
  height: 40px;
`;
