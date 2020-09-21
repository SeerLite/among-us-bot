import pymumble_py3 as pymumble
from pymumble_py3.constants import PYMUMBLE_CLBK_USERCREATED as USER_CREATED
from pymumble_py3.constants import PYMUMBLE_CLBK_USERUPDATED as USER_UPDATED
from pymumble_py3.constants import PYMUMBLE_CLBK_USERREMOVED as USER_REMOVED
from pymumble_py3.constants import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED as MSG_RCV

import timeit
import configparser
import sys

config = configparser.ConfigParser(allow_no_value=True)
config.read("config.ini")

config_file_regenerated = False
for section in ("connect", "login", "track"):
    if section not in config.sections():
        config[section] = {}
        config_file_regenerated = True

config["connect"]["host"] = config["connect"].get("host", "localhost")
config["connect"]["port"] = config["connect"].get("port", "64738")

config["login"]["username"] = config["login"].get("username", "Among Us Bot")
config["login"]["password"] = config["login"].get("password", "")
config["login"]["certfile"] = config["login"].get("certfile", "")
config["login"]["keyfile"] = config["login"].get("keyfile", "")

config["track"]["channel"] = config["track"].get("channel", "Among Us")

try:
    with open("config.ini", "x") as config_file:
        config.write(config_file, space_around_delimiters=True)
        print("Default configuration has been written to config.ini. Edit the necessary values and then run the bot again.")
        sys.exit(0)
except FileExistsError:
    with open("config.ini", "w") as config_file:
        config.write(config_file, space_around_delimiters=True)
        if config_file_regenerated:
            print("Some sections were missing from config.ini and have been regenerated. If it's all good, run the bot again.")
            sys.exit(0)

client = pymumble.Mumble(
    config["connect"].get("host"),
    config["login"].get("username"),
    port=config["connect"].getint("port"),
    password=config["login"].get("password", None),
    certfile=config["login"].get("certfile", None),
    keyfile=config["login"].get("keyfile", None)
    )

listened_user = None
listened_user_deafen_time = timeit.default_timer() - 1
muting = False


def set_muting(mute=muting):
    global muting
    muting = mute
    # I'm checking for muting outside of the for loop because I figured that'd
    # be faster
    if mute:
        for user in tracked_channel.get_users():
            user.mute()
    else:
        for user in tracked_channel.get_users():
            user.unmute()


def on_user_event(user, modifications=None):
    global listened_user
    global tracked_channel
    global listened_user_deafen_time

    if listened_user is None:
        return

    if listened_user not in (user["session"] for user in tracked_channel.get_users()):
        listened_user = None
    elif user["session"] == listened_user and modifications and "self_deaf" in modifications:
        if modifications["self_deaf"]:
            listened_user_deafen_time = timeit.default_timer()
        else:
            if timeit.default_timer() - listened_user_deafen_time < 1:
                set_muting(not muting)


def on_message(message):
    global listened_user
    global tracked_channel

    for user in tracked_channel.get_users():
        if message.actor == user["session"]:
            if message.message == "among:listen":
                if listened_user == message.actor:
                    listened_user = None
                    tracked_channel.send_text_message(f"No longer listening to {user['name']}.")
                elif listened_user is None:
                    listened_user = message.actor
                    tracked_channel.send_text_message(f"Now listening to {user['name']} for quick-toggle event! Quickly deafen and undeafen yourself to toggle mute!")
            elif message.message == "among:mute":
                set_muting(True)
            elif message.message == "among:unmute":
                set_muting(False)
            elif message.message == "among:toggle":
                set_muting(not muting)
            break


def toggle_mute(user):
    global listened_user
    global tracked_channel

    if not user.get_property("deaf"):
        user.deafen()
    else:
        user.unmute()


if __name__ == "__main__":
    client.start()
    try:
        client.is_ready()
        print(f"{config['login'].get('username')} is online!")

        if config["login"]["certfile"] and config["login"]["keyfile"]:
            client.users.myself.register()
            print("Registration request sent.")

        tracked_channel = client.channels.find_by_name(config["track"].get("channel"))
        tracked_channel.move_in()
        print(f"Tracking channel {repr(config['track'].get('channel'))}")

        client.callbacks.set_callback(USER_CREATED, on_user_event)
        client.callbacks.set_callback(USER_UPDATED, on_user_event)
        client.callbacks.set_callback(USER_REMOVED, on_user_event)

        client.callbacks.set_callback(MSG_RCV, on_message)

        client.join()
    except KeyboardInterrupt:
        client.stop()
