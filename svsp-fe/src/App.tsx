import NavigationBar from "@components/NavigationBar";
import Router from "@router/Router";
import { BrowserRouter } from "react-router-dom";

function App() {
  return (
    <BrowserRouter>
      <NavigationBar />
      <Router />
    </BrowserRouter>
  );
}

export default App;
