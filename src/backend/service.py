# service.py
#
# Copyright 2020 Dominik Schütz <do.sch.dev@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later


import _thread
import asyncio
import hangups

from gi.repository import Gio, GLib
from gi.repository.GLib import idle_add
from hangups import Client as HangupsClient, GoogleAuthError, NetworkError
from hangups import ChatMessageEvent

from ..backend.token_storage import TokenStorage
from ..backend.clientwrapper import Client
from ..backend.conversationlistwrapper import ConversationList
from ..backend.conversationwrapper import Conversation

class Service(object):

    __token_storage = None
    __hangups_running = False
    __asyncio_queue = None
    __asyncio_loop = None

    __client = None
    __user_list = None
    __conversation_list = None

    __notification_callbacks = list()
    __get_conversation_callbacks = list()
    __get_userlist_callbacks = list()

    __lists_lock = _thread.allocate_lock()

    def __init__(self):
        self.__token_storage = TokenStorage()
        self.__token_storage.get_refresh_token(self.__obtain_refresh_token)


    def __obtain_refresh_token(self, token, user_data=None):
        if token:
            # start hangups if token is avaliable
            _thread.start_new_thread(self.__bootup_hangups, (token,))


    def __bootup_hangups(self, refresh_token=None, oauth_code=None):
        # prevents Application from exiting
        Gio.Application.get_default().hold()
        self.__hangups_running = True
        try:
            # those classes will make hangups use TokenStorage with libsecret
            class CredentialsPrompt:
                def get_authorization_code():
                    return oauth_code

            class RefreshTokenCache:
                def get():
                    return refresh_token

                def set(new_refresh_token):
                    self.__token_storage.store_refresh_token(new_refresh_token)

            # get cookies from login
            cookies = hangups.get_auth(
                CredentialsPrompt,
                RefreshTokenCache,
                manual_login=True
            )

            # get hangups client
            hangups_client = HangupsClient(cookies)

            async def start_hangups_client():

                # cache loop and queue
                self.__asyncio_loop = asyncio.get_running_loop()
                self.__asyncio_queue = asyncio.Queue(loop=self.__asyncio_loop)
                self.__asyncio_queue.continue_queue = True

                # wait for hangouts to connect or raise an exception
                on_connect = asyncio.Future()
                hangups_client.on_connect.add_observer(
                    lambda: on_connect.set_result(None)
                )


                # debug
                hangups_client.on_disconnect.add_observer(
                    lambda: print("disconnect event")
                )

                # builds up client and calls waiting callbacks
                async def build_client():
                    # build user and conversation list
                    ret = await hangups.build_user_conversation_list(
                        hangups_client
                    )
                    user_list, conversation_list = ret

                    # create wrapper objects
                    self.__client = Client(hangups_client, self.__asyncio_queue)
                    with self.__lists_lock:
                        self.__conversation_list = ConversationList(
                            conversation_list, self.__asyncio_queue
                        )
                        self.__user_list = user_list

                    # give lists to waiting clients
                    for cb in self.__get_conversation_callbacks:
                        idle_add(cb, self.__conversation_list)
                    for cb in self.__get_userlist_callbacks:
                        idle_add(cb, self.__user_list)

                    # remove callbacks
                    self.__get_conversation_callbacks.clear()
                    self.__get_userlist_callbacks.clear()

                    # enable notifications
                    conversation_list.on_event.add_observer(
                        self.__incoming_event
                    )


                # work through queue
                async def run_queue():
                    queue = self.__asyncio_queue
                    while not queue.empty() or queue.continue_queue:
                        coro = await queue.get()
                        await coro

                # create tasks
                connect_task = asyncio.create_task(hangups_client.connect())
                build_client_task = asyncio.create_task(build_client())
                run_queue_task = asyncio.create_task(run_queue())

                tasks = (
                    on_connect,
                    connect_task,
                    build_client_task,
                    run_queue_task
                )

                print("pre wait")
                # wait until connected
                done, _ = await asyncio.wait(
                    tasks,
                    return_when=asyncio.ALL_COMPLETED
                )
                print("post wait")


            asyncio.run(start_hangups_client())

        except GoogleAuthError as e:
            print("GoogleAuthError: ")
            print(e)
            raise e
        except NetworkError as e:
            print("NetworkError: ")
            print(e)
            raise e
        except Exception as e:
            print("Exception: ")
            print(e)
            raise e

        self.__hangups_running = False
        Gio.Application.get_default().release()


    def __incoming_event(self, event):
        print("incoming event: ", event)
        emmiter = self.__user_list.get_user(event.user_id)
        app = Gio.Application.get_default()
        win = app.props.active_window
        if isinstance(event, ChatMessageEvent):
            if not emmiter.is_self or win and win.props.is_active:
                title = emmiter.full_name

                notification: Gio.Notification = Gio.Notification.new(title)
                notification.set_body(event.text)
                notification.set_priority(Gio.NotificationPriority.HIGH)
                notification.set_default_action_and_target(
                    "app.show-conversation",
                    GLib.Variant.new_string(event.conversation_id)
                )
                app.send_notification(
                    event.conversation_id,
                    notification
                )
                print("noti sent")


    def tell_oauth_token(self, oauth):
        _thread.start_new_thread(__bootup_hangups, (None, oauth))


    def get_conversation_list_async(self, callback):
        with self.__lists_lock:
            if self.__conversation_list:
                # conversation list is loaded
                idle_add(callback, self.__conversation_list)
            else:
                # is loading
                self.__get_conversation_callbacks.append(callback)


    def get_userlist_async(self, callback):
        if self.__user_list:
            idle_add(callback, self.__user_list)
        else:
            self.__get_userlist_callbacks.append(callback)


    def quit(self):
        self.__client.disconnect()


    def logout(self):
        self.__token_storage.reset_refresh_token()
        self.quit()
