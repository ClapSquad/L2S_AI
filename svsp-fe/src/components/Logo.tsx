import styled from "styled-components";
import favicon from "public/favicon.png";

export default function Logo({ size }: { size: string }) {
  const Logo = styled.img`
    width: ${size};
  `;

  return <Logo src={favicon} alt="Logo" />;
}
