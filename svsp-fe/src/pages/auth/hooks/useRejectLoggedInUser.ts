import { toast } from "react-toastify";
import { useNavigateBack } from "@hooks/userNavigateBack";
import { useIsLoggedIn } from "@hooks/useIsLoggedIn";
import { useEffect } from "react";

export function useRejectLoggedInUser() {
  const navigateBack = useNavigateBack();
  const isLoggedIn = useIsLoggedIn();
  useEffect(() => {
    if (isLoggedIn) {
      toast.info("이미 로그인 되어 있습니다");
      navigateBack();
    }
  }, [isLoggedIn]);
}
