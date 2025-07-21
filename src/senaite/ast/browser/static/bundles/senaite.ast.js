/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	// The require scope
/******/ 	var __webpack_require__ = {};
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/compat get default export */
/******/ 	(() => {
/******/ 		// getDefaultExport function for compatibility with non-harmony modules
/******/ 		__webpack_require__.n = (module) => {
/******/ 			var getter = module && module.__esModule ?
/******/ 				() => (module['default']) :
/******/ 				() => (module);
/******/ 			__webpack_require__.d(getter, { a: getter });
/******/ 			return getter;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/************************************************************************/
// This entry needs to be wrapped in an IIFE because it needs to be isolated against other entry modules.
(() => {

;// external "jQuery"
const external_jQuery_namespaceObject = jQuery;
var external_jQuery_default = /*#__PURE__*/__webpack_require__.n(external_jQuery_namespaceObject);
;// ./components/astpanelassign.coffee
function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _classCallCheck(a, n) { if (!(a instanceof n)) throw new TypeError("Cannot call a class as a function"); }
function _defineProperties(e, r) { for (var t = 0; t < r.length; t++) { var o = r[t]; o.enumerable = o.enumerable || !1, o.configurable = !0, "value" in o && (o.writable = !0), Object.defineProperty(e, _toPropertyKey(o.key), o); } }
function _createClass(e, r, t) { return r && _defineProperties(e.prototype, r), t && _defineProperties(e, t), Object.defineProperty(e, "prototype", { writable: !1 }), e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
var ASTPanelAssignController;


/*
Controller for the assignment of an AST panel to a Sample
*/
ASTPanelAssignController = /*#__PURE__*/function () {
  function ASTPanelAssignController() {
    _classCallCheck(this, ASTPanelAssignController);
    /*
    Binds callbacks on elements
    Attaches all the events to the body and refine the selector to delegate the
    event: https://learn.jquery.com/events/event-delegation/
    */
    this.bind_event_handler = this.bind_event_handler.bind(this);
    /*
    Event triggered when the button "add" next to ast panel selector is clicked
    System automatically adds the AST analyses to the sample based on the
    configuration of the selected panel
    */
    this.on_add_click = this.on_add_click.bind(this);
    /*
    Adds the panel to current context
    */
    this.add_ast_panel = this.add_ast_panel.bind(this);
    /*
    Ajax Submit with automatic event triggering and some sane defaults
    */
    this.ajax_submit = this.ajax_submit.bind(this);
    /*
    Returns whether this controller needs to be loaded or not
    */
    this.is_required = this.is_required.bind(this);
    /*
    Returns the panel selector element
    */
    this.get_panel_selector = this.get_panel_selector.bind(this);
    /*
    Returns the current url
    */
    this.get_current_url = this.get_current_url.bind(this);
    /*
    Prints a debug message in console with this component name prefixed
    */
    this.debug = this.debug.bind(this);
    this.ast_panel_selector = "select[id=ast_panel_selector]";
    this.ast_panel_add_button = "button[id=astpanel_add]";
    this.ast_panel_listing = "div[data-form_id='ast_analyses']";
    // Do not load this controller unless required
    if (!this.is_required()) {
      return;
    }
    this.debug("load");
    // Bind the event handler to the elements
    this.bind_event_handler();
    return this;
  }
  return _createClass(ASTPanelAssignController, [{
    key: "bind_event_handler",
    value: function bind_event_handler() {
      this.debug("bind_event_handler");
      return external_jQuery_default()("body").on("click", this.ast_panel_add_button, this.on_add_click);
    }
  }, {
    key: "on_add_click",
    value: function on_add_click(event) {
      var el, panel_uid, selector;
      event.preventDefault();
      this.debug("on_add_click");
      el = event.currentTarget;
      // Get the selected panel
      selector = this.get_panel_selector();
      panel_uid = selector.value;
      if (!panel_uid) {
        return;
      }
      // Call the assignment endpoint
      return this.add_ast_panel(panel_uid).done(function (data) {
        var listing;
        // Update the analyses listing
        listing = document.querySelector(this.ast_panel_listing);
        this.debug(listing);
        event = new Event("reload");
        return listing.dispatchEvent(event);
      });
    }
  }, {
    key: "add_ast_panel",
    value: function add_ast_panel(panel_uid) {
      var deferred, options;
      this.debug("add_ast_panel:panel_uid:".concat(panel_uid));
      deferred = external_jQuery_default().Deferred();
      options = {
        url: this.get_current_url() + "/add_ast_panel",
        data: {
          panel_uid: panel_uid
        }
      };
      this.ajax_submit(options).done(function (data) {
        return deferred.resolveWith(this, [[]]);
      });
      return deferred.promise();
    }
  }, {
    key: "ajax_submit",
    value: function ajax_submit() {
      var options = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};
      var done;
      this.debug("ajax_submit");
      // some sane option defaults
      if (options.type == null) {
        options.type = "POST";
      }
      if (options.context == null) {
        options.context = this;
      }
      if (options.data == null) {
        options.data = {};
      }
      if (options._authenticator == null) {
        options._authenticator = external_jQuery_default()("input[name='_authenticator']").val();
      }
      this.debug(">>> ajax_submit::options=", options);
      external_jQuery_default()(this).trigger("ajax:submit:start");
      done = function done() {
        return external_jQuery_default()(this).trigger("ajax:submit:end");
      };
      return external_jQuery_default().ajax(options).done(done);
    }
  }, {
    key: "is_required",
    value: function is_required() {
      return this.get_panel_selector() != null;
    }
  }, {
    key: "get_panel_selector",
    value: function get_panel_selector() {
      return document.querySelector(this.ast_panel_selector);
    }
  }, {
    key: "get_current_url",
    value: function get_current_url() {
      var host, location, pathname, protocol;
      location = window.location;
      protocol = location.protocol;
      host = location.host;
      pathname = location.pathname;
      return "".concat(protocol, "//").concat(host).concat(pathname);
    }
  }, {
    key: "debug",
    value: function debug(message) {
      return console.debug("[senaite.ast]", "ASTPanelAssignController::".concat(message));
    }
  }]);
}();
/* harmony default export */ const astpanelassign_coffee = (ASTPanelAssignController);
;// ./senaite.ast.js

document.addEventListener("DOMContentLoaded", function () {
  console.debug("*** SENAITE AST JS LOADED ***");

  // Initialize controllers
  window.ast_panel_assign = new astpanelassign_coffee();
});
})();

// This entry needs to be wrapped in an IIFE because it needs to be isolated against other entry modules.
(() => {
// extracted by mini-css-extract-plugin

})();

/******/ })()
;
//# sourceMappingURL=senaite.ast.js.map