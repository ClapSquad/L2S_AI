import Router from "@router/Router";
import { ToastContainer } from "react-toastify";
import AuthContextProvider from "./contexts/AuthContext";

function App() {
  return (
    <AuthContextProvider>
      <Router />
      <ToastContainer />
    </AuthContextProvider>
  );
}

export default App;
