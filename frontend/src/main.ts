import { mount } from "svelte";
import App from "./App.svelte";
import "./app.css";
import { startRouter } from "./lib/router.svelte.ts";

startRouter();

mount(App, { target: document.getElementById("app")! }); // index.html always has #app
