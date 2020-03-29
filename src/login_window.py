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

from gi.repository import Gtk, Handy, WebKit2
from hangups import auth
# TODO: replace device_name=hangups with device_name=hangouts_gtk


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/login_window.ui")
class LoginWindow(Handy.Dialog):
    __gtype_name__ = "LoginWindow"

    intern_box = Gtk.Template.Child()
    intern_action_area = Gtk.Template.Child()

    oauth_code = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_size_request(500, 500)
        self.set_modal(True)
        self.set_transient_for(self.get_parent())

        self.__create_and_configure_webkit()

        self.show()

    def __create_and_configure_webkit(self):
        web_view = WebKit2.WebView()
        web_view.set_size_request(50, 50)
        web_view.set_vexpand(True)
        web_view.set_hexpand(True)
        web_view.set_editable(False)
        cookie_manager = web_view.get_context().get_cookie_manager()

        def cookies_got(cookie_manager, result, _):
            data = cookie_manager.get_cookies_finish(result)
            cookies = {d.get_name(): d.get_value() for d in data}
            oauth_code = cookies.get("oauth_code", None)
            if oauth_code:
                self.oauth_code = oauth_code
                self.response(Gtk.ResponseType.OK)
                # delete cookies
                web_view.get_website_data_manager().clear(WebKit2.WebsiteDataTypes.COOKIES, 0)

        def cookie_changed(cookie_manager):
            cookie_manager.get_cookies("https://accounts.google.com/o/oauth2/programmatic_auth", None, cookies_got, None)

        cookie_manager.connect("changed", cookie_changed)

        web_view.load_uri(auth.OAUTH2_LOGIN_URL)
        # web_view.load_uri("https://www.google.com")
        web_view.show()
        self.intern_box.add(web_view)
