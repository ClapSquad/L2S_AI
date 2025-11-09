import { useState } from "react";
import styled from "styled-components";

export function ToggleButton() {
  const [isOn, setIsOn] = useState(false);

  return <Switch isOn={isOn} onClick={() => setIsOn(!isOn)} />;
}

const Switch = styled.button<{ isOn: boolean }>`
  width: 60px;
  height: 30px;
  border-radius: 15px;
  border: none;
  cursor: pointer;
  background-color: ${({ isOn }) => (isOn ? "green" : "gray")};
  position: relative;
  transition: background-color 0.3s;

  &::after {
    content: "";
    position: absolute;
    top: 3px;
    left: ${({ isOn }) => (isOn ? "32px" : "3px")};
    width: 24px;
    height: 24px;
    background: white;
    border-radius: 50%;
    transition: left 0.3s;
  }
`;
