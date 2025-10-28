import type { ReactNode } from "react";
import styled from "styled-components";

type ModalProps = {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
};

export function Modal({ isOpen, onClose, children }: ModalProps) {
  if (!isOpen) return null;

  return (
    <ModalWrapper onClick={onClose}>
      <ModalWindow onClick={(e) => e.stopPropagation()}>{children}</ModalWindow>
    </ModalWrapper>
  );
}

const ModalWrapper = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
`;

const ModalWindow = styled.div`
  box-shadow: inset;
  position: relative;
`;
