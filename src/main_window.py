# This file is part of Hangouts GTK
# Copyright © 2019-2020 Dominik Schütz <do.sch.dev@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Handy, Gio, GLib

from hangups.conversation_event import (ChatMessageEvent, HangoutEvent)

from .backend.image_cache import ImageCache
from .backend.service import Service

from .widgets.conversation_sidebar_element import ConversationSidebarElement
from .widgets.conversation_sidebar import ConversationSidebar
from .widgets.message_box import MessageBox
from .widgets.conversation_edit_panel import ConversationEditPanel


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/main_window.ui")
class MainWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "MainWindow"

    handybar: Handy.TitleBar = Gtk.Template.Child()
    leaflet: Handy.Leaflet = Gtk.Template.Child()
    header: Gtk.HeaderBar = Gtk.Template.Child()
    panel_headerbar: Gtk.HeaderBar = Gtk.Template.Child()
    main_stack: Gtk.Stack = Gtk.Template.Child()
    login_button: Gtk.Button = Gtk.Template.Child()
    content_box: Handy.Leaflet = Gtk.Template.Child()
    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()
    conversation_list_viewport: Gtk.Viewport = Gtk.Template.Child()
    message_view: Gtk.Stack = Gtk.Template.Child()
    back: Gtk.Button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    group_button: Gtk.Button = Gtk.Template.Child()
    hangout_button: Gtk.Button = Gtk.Template.Child()


    def __init__(self, service, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__assemble_login()
        self.__assemble_sidebar()
        self.__assemble_header_bar_elements()

        self.__add_actions()

        #self.set_size_request(300, 500)
        self.set_default_size(800, 600)

        # create ImageCache
        self.__image_cache = ImageCache()

        # communicate with hangups
        self.__service = service
        self.__service.get_conversation_list_async(self.__get_conversation_list)
        self.__active_id = None
        self.__conversation_list = None


    def __assemble_header_bar_elements(self):
        # back button of right back button
        def set_left_side_visible(button):
            self.leaflet.set_visible_child(self.header)
            self.content_box.set_visible_child(self.scrolled_window)

        self.back.connect("clicked", set_left_side_visible)

        # group edit window
        def open_conversation_edit_window(button):
            conversation_edit_window = Handy.Dialog(
                application=self.get_application(),
                parent=self,
                icon_name=self.get_icon_name,
                flags=Gtk.DialogFlags.MODAL | \
                    Gtk.DialogFlags.DESTROY_WITH_PARENT | \
                    Gtk.DialogFlags.USE_HEADER_BAR
            )

            # add content to dialog
            conversation_edit_window.get_content_area().add(
                ConversationEditPanel(
                    self.__conversations[self.__active_id],
                    self.__image_cache
                )
            )

            # run Dialog
            conversation_edit_window.run()
            conversation_edit_window.destroy()

        self.group_button.connect("clicked", open_conversation_edit_window)

        menu = Gtk.Builder() \
            .new_from_resource("/com/dosch/HangoutsGTK/ui/popover_menu.ui") \
            .get_object("popover_menu")
        popover_menu = Gtk.Popover.new_from_model(self.menu_button, menu)
        self.menu_button.set_popover(popover_menu)

        # show and hide back button on fold and unfold
        self.leaflet.connect(
            "notify::folded",
            lambda _, fold: \
                self.back.set_visible(self.leaflet.get_property("folded")))
        #self.back.set_visible(self.leaflet.get_property("hhomogeneous-folded"))

        # handle click on call button
        def hangout_button_clicked(button):
            for c in self.__message_boxes:
                conv_id = c
            return
            uri = "https://plus.google.com/hangouts/_/CONVERSATION/#{0}"\
                .format(conv_id)
            Gio.AppInfo.launch_default_for_uri(uri)

        self.hangout_button.connect("clicked", hangout_button_clicked)


    def __assemble_sidebar(self):
        # create sidebar
        self.conversation_sidebar = ConversationSidebar()
        self.conversation_list_viewport.add(self.conversation_sidebar)

        # handle click on sidebar element
        def selected(box, row: Gtk.ListBoxRow):
            # show correct chat
            sidebar_element = row.get_children()[0]
            conv_id = sidebar_element.get_id()

            # open correct box
            self.__open_message_box(None, GLib.Variant("s", conv_id))

            # show conversation edit button
            # self.group_button.set_visible(True)

        self.conversation_sidebar.connect(
            "row-activated",
            selected
        )

        # handle focus
        def focused(window, event):
            visible_child = self.message_view.get_visible_child()
            if isinstance(visible_child, MessageBox):
                visible_child.map(visible_child)

        self.connect("focus-in-event", focused)


    def __assemble_login(self):

        self.login_window = None

        # handler for login_button clicked-signal
        def login_button_clicked(button):
            from .login_window import LoginWindow
            # create LoginDialog
            self.login_window = LoginWindow(
                application=self.get_application(),
                title="Log In",
                parent=self,
                icon_name=self.get_icon_name,
                flags=Gtk.DialogFlags.MODAL | \
                    Gtk.DialogFlags.DESTROY_WITH_PARENT | \
                    Gtk.DialogFlags.USE_HEADER_BAR
            )

            # run Dialog
            response = self.login_window.run()
            # save oauth_code
            oauth_code = self.login_window.oauth_code
            self.login_window.destroy()

            # got oauth_code
            if response == Gtk.ResponseType.OK:
                self.main_stack.set_visible_child_name("loading_state")
                self.__service.tell_oauth_token(oauth_code)

        # connect handler to signal
        self.login_button.connect("clicked", login_button_clicked)

    def has_focus(self):
        return self.props.has_toplevel_focus


    def __get_conversation_list(self, conversation_list):

        if conversation_list is None:
            self.main_stack.set_visible_child_name("login_page")
            return

        self.__service.set_active()

        self.__conversation_list = conversation_list
        for conversation in conversation_list.get_all():
            self.conversation_sidebar.prepend(
                ConversationSidebarElement(
                    self, conversation, self.__image_cache
                )
            )

        self.conversation_sidebar.show()
        self.main_stack.set_visible_child_name("content_box")

        if self.__active_id:
            self.__open_message_box(
                None,
                GLib.Variant("s", self.__active_id)
            )

        self.leaflet.show()


    def __logout(self):
        self.main_stack.set_visible_child_name("login_page")
        self.message_view.foreach(
            lambda child, x: self.message_view.remove(child), None
        )
        #TODO: sidebar
        self.conversation_list_viewport.remove(self.conversation_sidebar)
        self.__conversations = {}
        self.__client = None
        self.__active_id = None
        # disable logout
        self.lookup_action("logout").set_enabled(False)


    def __open_message_box(self, _action, variant):

        # get conversation_id
        conversation_id = variant.get_string()

        # come back later if __conversation_list ist not set
        if not self.__conversation_list:
            self.__active_id = conversation_id
            return

        # current conversation
        conversation = self.__conversation_list.get(conversation_id)

        # select matching row
        def select_matching_row(row):
            if row.get_children()[0].get_id() == conversation_id:
                self.conversation_sidebar.select_row(row)
        self.conversation_sidebar.foreach(select_matching_row)

        # create message_box if not exists
        if not self.message_view.get_child_by_name(conversation_id):
            # create message_box
            msg_box = MessageBox(conversation, self.__image_cache)
            self.message_view.add_named(msg_box, conversation_id)

        self.message_view.set_visible_child_name(conversation_id)
        self.__active_id = conversation_id

        # show chat side of leaflets
        self.leaflet.set_visible_child(self.panel_headerbar)
        self.content_box.set_visible_child(self.message_view)

        # handle right header bar
        if conversation.name:
            self.panel_headerbar.set_title(conversation.name)
        else:
            self.panel_headerbar.set_title(", ".join(
                map(lambda u: u.full_name,
                    filter(lambda u: not u.is_self, conversation.users)
            )))


    def __add_actions(self):
        show_conversation = Gio.SimpleAction.new(
            "show-conversation",
            GLib.VariantType.new("s")
        )
        show_conversation.connect("activate", self.__open_message_box)
        self.add_action(show_conversation)

        quit = Gio.SimpleAction.new("quit")
        quit.set_enabled(True)
        quit.connect("activate", lambda a, v: self.destroy())
        self.add_action(quit)

        logout = Gio.SimpleAction.new("logout")
        logout.set_enabled(True)
        logout.connect("activate", lambda a, v: self.logout())
        self.add_action(logout)
