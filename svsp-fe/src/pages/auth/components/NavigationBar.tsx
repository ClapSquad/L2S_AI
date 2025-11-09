import styled from "styled-components";
import { globalButtonStyle } from "@styles/globalStyle";
import { SettingsIcon } from "src/icons/SettingsIcon";
import { useModal } from "@hooks/useModal";
import { Modal } from "@components/Modal";
import SettingModal from "@components/SettingModal";
import { ArrowBackIcon } from "src/icons/ArrowBackIcon";
import { useNavigateBack } from "@hooks/userNavigateBack";

export default function NavigationBar() {
  const navigateBack = useNavigateBack();
  const { isOpen, open, close } = useModal();

  return (
    <>
      <Modal isOpen={isOpen} onClose={close}>
        <SettingModal onClose={close} />
      </Modal>
      <NavigationBarWrapper>
        <Button onClick={() => navigateBack()}>
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
