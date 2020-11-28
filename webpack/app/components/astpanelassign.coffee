import $ from "jquery"

###
Controller for the assignment of an AST panel to a Sample
###
class ASTPanelAssignController

  constructor: ->
    @ast_panel_selector = "select[id=ast_panel_selector]"
    @ast_panel_add_button =  "button[id=astpanel_add]"
    @ast_panel_listing = "div[data-form_id='ast_analyses']"

    # Do not load this controller unless required
    return unless @is_required()

    @debug "load"

    # Bind the event handler to the elements
    @bind_event_handler()

    return @

  ###
  Binds callbacks on elements
  Attaches all the events to the body and refine the selector to delegate the
  event: https://learn.jquery.com/events/event-delegation/
  ###
  bind_event_handler: =>
    @debug "bind_event_handler"
    $("body").on "click", @ast_panel_add_button, @on_add_click

  ###
  Event triggered when the button "add" next to ast panel selector is clicked
  System automatically adds the AST analyses to the sample based on the
  configuration of the selected panel
  ###
  on_add_click: (event) =>
    event.preventDefault()
    @debug "on_add_click"
    el = event.currentTarget

    # Get the selected panel
    selector = @get_panel_selector()
    panel_uid = selector.value
    return unless panel_uid

    # Call the assignment endpoint
    @add_ast_panel panel_uid
    .done (data) ->
      # Update the analyses listing
      listing = document.querySelector @ast_panel_listing
      @debug listing
      event = new Event "reload"
      listing.dispatchEvent event

  ###
  Adds the panel to current context
  ###
  add_ast_panel: (panel_uid) =>
    @debug "add_ast_panel:panel_uid:#{ panel_uid }"
    deferred = $.Deferred()
    options =
      url: @get_current_url()+"/add_ast_panel"
      data:
        panel_uid: panel_uid

    @ajax_submit options
    .done (data) ->
      return deferred.resolveWith this, [[]]

    deferred.promise()

  ###
  Ajax Submit with automatic event triggering and some sane defaults
  ###
  ajax_submit: (options={}) =>
    @debug "ajax_submit"

    # some sane option defaults
    options.type ?= "POST"
    options.context ?= this
    options.data ?= {}
    options._authenticator ?= $("input[name='_authenticator']").val()

    @debug ">>> ajax_submit::options=", options

    $(this).trigger "ajax:submit:start"
    done = ->
      $(this).trigger "ajax:submit:end"
    return $.ajax(options).done done

  ###
  Returns whether this controller needs to be loaded or not
  ###
  is_required: =>
    return @get_panel_selector()?

  ###
  Returns the panel selector element
  ###
  get_panel_selector: =>
    return document.querySelector @ast_panel_selector

  ###
  Returns the current url
  ###
  get_current_url: =>
    location = window.location
    protocol = location.protocol
    host = location.host
    pathname = location.pathname
    return "#{protocol}//#{host}#{pathname}"

  ###
  Prints a debug message in console with this component name prefixed
  ###
  debug: (message) =>
    console.debug "[senaite.ast]", "ASTPanelAssignController::#{ message }"

export default ASTPanelAssignController
