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

from gi.repository import Gtk

from ..widgets.conversation_edit_user_element import ConversationEditUserElement


@Gtk.Template(resource_path="/com/dosch/HangoutsGTK/ui/conversation_edit_panel.ui")
class ConversationEditPanel(Gtk.Box):

    __gtype_name__ = "ConversationEditPanel"

    group_name: Gtk.Entry = Gtk.Template.Child()
    group_add_button: Gtk.Button = Gtk.Template.Child()
    user_list: Gtk.ListBox = Gtk.Template.Child()

    def __init__(self, conversation, image_cache, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if conversation.name:
            self.group_name.set_text(conversation.name)

        for user in filter(lambda u: not u.is_self, conversation.users):
            self.user_list.add(ConversationEditUserElement(user, image_cache))

        self.show()
