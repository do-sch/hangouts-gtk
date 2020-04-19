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

import gi
import _thread

gi.require_version("Secret", "1")

from gi.repository import Secret

from ..backend.hangoutslogger import HangoutsLogger


class TokenStorage():

    SECRET_SCHEMA = Secret.Schema.new(
        name="com.dosch.HangoutsGTK.refresh_token",
        flags=Secret.SchemaFlags.NONE,
        attribute_names_and_types={"refresh_token": Secret.SchemaAttributeType.STRING}
    )

    def __init__(self):
        self.__log = HangoutsLogger()
        self.__token_cache = None


    def store_refresh_token(self, token):
        Secret.password_store(self.SECRET_SCHEMA, {}, None, "refresh_token", token, None, None, None)


    def get_refresh_token(self, callback, user_data=None):
        #def secret_callback(source_object, result, user_data):
        #    self.__log.debug("looked up in secret")
        #    self._token_cache = Secret.password_lookup_finish(result)
        #    self.__log.debug("lookup finish")
        #    callback(self._token_cache, user_data)
        #Secret.password_lookup(self.SECRET_SCHEMA, {}, None, secret_callback, user_data)
        #self.__log.debug("lookup in secret")
        def secret_thread(callback, user_data):
            self.__log.debug("secret thread here")
            self.__token_cache = Secret.password_lookup_sync(
                self.SECRET_SCHEMA, {}, None
            )
            self.__log.debug("got secret")
            callback(self.__token_cache, user_data)

        self.__log.debug("starting secret thread")
        _thread.start_new_thread(secret_thread, (callback, user_data))


    def get_refresh_token_cached(self, callback, user_data=None):
        if self._token_cache is NotImplemented:
            self.get_refresh_token(callback, user_data)
        else:
            _thread.start_new_thread(callback, (self.__token_cache, user_data))


    def reset_refresh_token(self):
        Secret.password_clear(self.SECRET_SCHEMA, {}, None, None, None)
