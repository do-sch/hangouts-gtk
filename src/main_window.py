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

from .backend.image_cache import ImageCache
from .backend.hangupswrapper import start_client
from .backend.token_storage import TokenStorage

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

    conversation_sidebar = NotImplemented

    login_window = NotImplemented

    token_storage = None
    __client = None

    __active_id = None
    __conversations = {}

    __message_boxes = {}
    __image_cache = NotImplemented
    __disconnect_handler = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__assemble_login()
        self.__assemble_sidebar()
        self.__assemble_header_bar_elements()

        self.set_size_request(300, 500)

        # handle existing refresh_token
        def get_token(token, user_data=None):
            print("got token")
            # nobody was logged in previously
            if not token:
                self.main_stack.set_visible_child_name("login_page")
            # create client from token stuff
            else:
                def get_userlist_conversationlist(client, userlist, conversationlist):
                    print("logged in")
                    self.set_client_userlist_conversationlist(client, userlist, conversationlist)

                start_client(
                    (get_userlist_conversationlist, self.auth_error, self.network_error, self.undefined_error),
                    self.token_storage
                )

        # call TokenStorage to asynchronously get refresh_token from storage
        self.token_storage = TokenStorage()
        self.token_storage.get_refresh_token(get_token)

        # handle click on call button
        def hangout_button_clicked(button):
            for c in self.__message_boxes:
                print(c)
                conv_id = c
            return
            uri = "https://plus.google.com/hangouts/_/CONVERSATION/#{0}".format(conv_id)
            Gio.AppInfo.launch_default_for_uri(uri)

        self.hangout_button.connect("clicked", hangout_button_clicked)

        # create ImageCache
        self.__image_cache = ImageCache()

        # handle focus
        def focused(window, event):
            visible_child = self.message_view.get_visible_child()
            if isinstance(visible_child, MessageBox):
                visible_child.focus()

        self.connect("focus-in-event", focused)

        # add actions
        show_conversation_action = Gio.SimpleAction.new("show-conversation", GLib.VariantType.new('s'))
        show_conversation_action.connect("activate", self.__notification_clicked)
        self.props.application.add_action(show_conversation_action)

        logout = Gio.SimpleAction.new("logout")
        logout.set_enabled(False)
        logout.connect("activate", lambda action, val: self.logout())
        self.add_action(logout)

        quit = Gio.SimpleAction.new("quit")
        quit.set_enabled(True)
        quit.connect("activate", lambda action, val: self.destroy())
        self.add_action(quit)

        # prevent Application from being destroyed by clicking close
        def on_close(window, event):
            if self.main_stack.get_visible_child() is self.content_box:
                self.hide();
                return True

            return False

        self.connect("delete-event", on_close)
        print("init ready")

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
                flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.USE_HEADER_BAR,
            )

            # add content to dialog
            conversation_edit_window.get_content_area().add(ConversationEditPanel(
                self.__conversations[self.__active_id],
                self.__image_cache
            ))

            # run Dialog
            conversation_edit_window.run()
            conversation_edit_window.destroy()

        self.group_button.connect("clicked", open_conversation_edit_window)

        menu = Gtk.Builder().new_from_resource("/com/dosch/HangoutsGTK/ui/popover_menu.ui").get_object("popover_menu")
        popover_menu = Gtk.Popover.new_from_model(self.menu_button, menu)
        self.menu_button.set_popover(popover_menu)

        # show and hide back button on fold and unfold
        self.leaflet.connect("notify::folded", lambda _, fold: self.back.set_visible(self.leaflet.get_property("folded")))
        self.back.set_visible(self.leaflet.get_property("hhomogeneous-folded"))

    def __assemble_sidebar(self):
        # create sidebar
        self.conversation_sidebar = ConversationSidebar()
        self.conversation_list_viewport.add(self.conversation_sidebar)

        # handle click on sidebar element
        def selected(box, row: Gtk.ListBoxRow):
            # show chat side of leaflets
            self.leaflet.set_visible_child(self.panel_headerbar)
            self.content_box.set_visible_child(self.message_view)

            # show correct chat
            sidebar_element = row.get_children()[0]
            self.__active_id = sidebar_element.get_id()

            # current conversation
            conversation = self.__conversations[self.__active_id]

            if not self.__message_boxes.get(self.__active_id):
                # create message_box
                msg_box = MessageBox(conversation, self.__image_cache)
                self.message_view.add_named(msg_box, self.__active_id)
                self.__message_boxes[self.__active_id] = msg_box

            self.message_view.set_visible_child_name(self.__active_id)

            # handle right header bar
            if conversation.name:
                self.panel_headerbar.set_title(conversation.name)
            else:
                self.panel_headerbar.set_title(", ".join(
                    map(lambda u: u.first_name,
                        filter(lambda u: not u.is_self, conversation.users)
                )))

            # show conversation edit button
            # self.group_button.set_visible(True)

        self.conversation_sidebar.connect(
            "row-activated",
            selected
        )

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
                flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.USE_HEADER_BAR
            )

            # run Dialog
            response = self.login_window.run()
            # save oauth_code
            oauth_code = self.login_window.oauth_code
            self.login_window.destroy()

            # got oauth_code
            if response == Gtk.ResponseType.OK:
                self.main_stack.set_visible_child_name("loading_state")
                start_client(
                    (self.set_client_userlist_conversationlist, self.auth_error, self.network_error, self.undefined_error),
                    self.token_storage,
                    oauth_code
                )

        # connect handler to signal
        self.login_button.connect("clicked", login_button_clicked)

    def has_focus(self):
        return self.props.has_toplevel_focus

    def set_client_userlist_conversationlist(self, client, user_list, conversation_list):
        # TODO: built userlist
        self.__client = client
        self.__disconnect_handler = self.connect("destroy", lambda *args: self.__client.disconnect())
        self.__client.set_active()
        for conversation in conversation_list.get_all():
            # add sidebar element
            self.conversation_sidebar.prepend(ConversationSidebarElement(self, conversation, self.__image_cache))

            conversation_id_str = str(conversation.id_)
            self.__conversations[conversation_id_str] = conversation

        self.conversation_sidebar.show_all()
        self.main_stack.set_visible_child_name("content_box")

        # set titlebar buttons visible
        self.leaflet.show()

        # enable logout
        self.lookup_action("logout").set_enabled(True)

    def logout(self):
        print("logout...")
        self.token_storage.reset_refresh_token()
        self.__client.disconnect()
        self.main_stack.set_visible_child_name("login_page")
        self.message_view.foreach(lambda child, x: self.message_view.remove(child), None)
        self.conversation_list_viewport.remove(self.conversation_sidebar)
        self.disconnect(self.__disconnect_handler)
        self.__conversations = {}
        self.__message_boxes = {}
        self.__client = None
        self.__active_id = None
        # disable logout
        self.lookup_action("logout").set_enabled(False)


    def __notification_clicked(self, action, variant: GLib.Variant):
        self.show()
        self.message_view.set_visible_child_name(variant.get_string())

    def auth_error(self):
        pass

    def network_error(self):
        pass

    def undefined_error(self):
        pass
