import ASTPanelAssignController from "./components/astpanelassign.coffee"

document.addEventListener("DOMContentLoaded", () => {
  console.debug("*** SENAITE AST JS LOADED ***");

  // Initialize controllers
  window.ast_panel_assign = new ASTPanelAssignController();

});
