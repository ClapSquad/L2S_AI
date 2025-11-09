import { useContext } from "react";
import { AuthContext } from "src/contexts/AuthContext";

export function useIsLoggedIn() {
  const { user } = useContext(AuthContext);
  return !!user;
}
