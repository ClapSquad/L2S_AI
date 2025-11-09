import { useNavigate } from "react-router-dom";
import routePath from "@router/routePath";

export function useNavigateBack() {
  const navigate = useNavigate();

  const navigateBack = () => {
    try {
      if (
        window.history.length > 1 &&
        document.referrer &&
        new URL(document.referrer).origin === window.location.origin
      ) {
        navigate(-1);
      } else {
        navigate(routePath.HOME, { replace: true });
      }
    } catch (e) {
      navigate(routePath.HOME, { replace: true });
    }
  };

  return navigateBack;
}
