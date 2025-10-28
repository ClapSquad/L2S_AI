import styled from "styled-components";
import favicon from "public/favicon.png";

export default function Logo({ size }: { size: string }) {
  return <LogoWrapper src={favicon} alt="Logo" size={size} />;
}

const LogoWrapper = styled.img<{ size: string }>`
  width: ${({ size }) => size};
`;
