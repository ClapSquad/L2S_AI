import { CloseIcon } from "src/icons/CloseIcon";
import styled from "styled-components";
import { globalButtonStyle } from "@styles/globalStyle";
import { ToggleButton } from "./Toggle";

export default function SettingModal({ onClose }: { onClose: () => void }) {
  return (
    <ModalWrapper>
      <TopBar>
        <Title>Setting</Title>
        <Button onClick={onClose}>
          <CloseIcon size="30" color="black" />
        </Button>
      </TopBar>
      <hr />
      <VerticalLayout>
        <HorizontalLayout>
          <label htmlFor="language-select">언어 선택</label>
          <select>
            <option value="">한국어</option>
            <option value="">English</option>
          </select>
        </HorizontalLayout>
        <HorizontalLayout>
          <label htmlFor="language-select">다크 모드</label>
          <ToggleButton />
        </HorizontalLayout>
      </VerticalLayout>
    </ModalWrapper>
  );
}

const Title = styled.div`
  font-weight: bold;
`;

const TopBar = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const Button = styled.button`
  ${globalButtonStyle}
`;

const VerticalLayout = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

const HorizontalLayout = styled.div`
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const ModalWrapper = styled.div`
  background-color: white;
  border-radius: 8px;
  padding: 20px;

  width: 300px;
`;
