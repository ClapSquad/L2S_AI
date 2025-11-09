import Router from "@router/Router";
import { ToastContainer } from "react-toastify";
import { useValidateAuth } from "@apis/hooks/useValidateAuth";

function App() {
  useValidateAuth();

  return (
    <>
      <Router />
      <ToastContainer />
    </>
  );
}

export default App;
