import { BrowserRouter } from "react-router-dom";
import NavigationBar from "./components/NavigationBar";
import Router from "./components/Router";

function App() {
  return (
    <BrowserRouter>
      <NavigationBar />
      <Router />
    </BrowserRouter>
  );
}

export default App;
