#!/usr/bin/env python3

# SPDX-License-Identifier: MIT

# Copyright (c) 2022 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)

import crtm_gui as gui
import crtm_cli as cli
import database as db
import utils as ut
import logging
import os


def button_handler(update, context):
    uid = ut.uid(update)
    query = update.callback_query
    if not db.cached(uid):
        ut.not_started_gui(update)
    else:
        if query.data == 'main_menu':
            gui.main_menu(update)
        elif query.data == 'weather_menu':
            gui.weather_menu(update)
        elif query.data == 'card_menu':
            gui.card_menu(update)
        elif query.data.startswith('train_menu'):
            args = query.data.split('_')
            gui.train_menu(update, args[-1])
        elif query.data.startswith('line_menu'):
            args = query.data.split('_')
            gui.train_line_menu(update, args[-2], args[-1])
        elif query.data.startswith('station_menu'):
            args = query.data.split('_')
            gui.train_station_menu(update, args[-3], args[-2], args[-1])
        elif query.data.startswith('time_train'):
            args = query.data.split('_')
            gui.train_time(update, args[-4], args[-3], args[-2], args[-1])
        elif query.data.startswith('bus_menu'):
            args = query.data.split('_')
            gui.bus_menu(update, args[-1])
        elif query.data.startswith('time_bus'):
            args = query.data.split('_')
            gui.bus_time(update, args[-2], args[-1])
        elif query.data.startswith('time_cli'):
            args = query.data.split('_')
            gui.cli_time(update, args[-2], args[-1])
        elif query.data == 'favorites_menu':
            gui.favorites_menu(update)
        elif query.data.startswith('fav_'):
            args = query.data.split('_')
            gui.add_favorite(update, args[-3], args[-2], args[-1])
        elif query.data.startswith('unfav_'):
            args = query.data.split('_')
            gui.del_favorite(update, args[-3], args[-2], args[-1])
        elif query.data.startswith('time_fav_'):
            args = query.data.split('_')
            gui.time_favorite_menu(update, args[-2], args[-1])
        elif query.data == 'nop':
            query.answer()


def setup_handlers(dispatch, job_queue):
    start_handler = CommandHandler('start', cli.start,
                                   filters=~Filters.update.edited_message)
    dispatch.add_handler(start_handler)

    menu_handler = CommandHandler('menu', cli.menu,
                                  filters=~Filters.update.edited_message)
    dispatch.add_handler(menu_handler)

    metro_handler = CommandHandler('metro', cli.times,
                                   filters=~Filters.update.edited_message)
    dispatch.add_handler(metro_handler)

    cerc_handler = CommandHandler('cercanias', cli.times,
                                  filters=~Filters.update.edited_message)
    dispatch.add_handler(cerc_handler)

    emt_handler = CommandHandler('emt', cli.times,
                                 filters=~Filters.update.edited_message)
    dispatch.add_handler(emt_handler)

    urb_handler = CommandHandler('interurbano', cli.times,
                                 filters=~Filters.update.edited_message)
    dispatch.add_handler(urb_handler)

    fav_handler = CommandHandler('favoritos', cli.favorites,
                                 filters=~Filters.update.edited_message)
    dispatch.add_handler(fav_handler)

    card_handler = CommandHandler('abono', cli.card,
                                  filters=~Filters.update.edited_message)
    dispatch.add_handler(card_handler)

    help_handler = CommandHandler('ayuda', cli.bot_help,
                                  filters=~Filters.update.edited_message)
    dispatch.add_handler(help_handler)

    suggest_handler = CommandHandler('sugerir', cli.suggest,
                                     filters=~Filters.update.edited_message)
    dispatch.add_handler(suggest_handler)

    donate_handler = CommandHandler('donar', cli.donate,
                                    filters=~Filters.update.edited_message)
    dispatch.add_handler(donate_handler)

    remove_handler = CommandHandler('borrar', cli.remove,
                                    filters=~Filters.update.edited_message)
    dispatch.add_handler(remove_handler)

    text_handler = MessageHandler(
        Filters.text & ~Filters.update.edited_message, cli.suggest_text)
    dispatch.add_handler(text_handler)

    dispatch.add_handler(CallbackQueryHandler(button_handler))


if __name__ == '__main__':
    logging.basicConfig(format=('%(asctime)s - %(name)s - '
                                '%(levelname)s - %(message)s'),
                        level=logging.INFO)

    if os.path.isfile(ut.FILES['cfg']):
        db.setup_db()
        updater = Updater(token=ut.config('bot'), use_context=True)
        dispatcher = updater.dispatcher
        setup_handlers(dispatcher, updater.job_queue)
        ut.load_data()
        ut.train_lines('metro')
        ut.train_lines('cerc')
        ut.bus_lines('emt')
        ut.bus_lines('urb')

        updater.start_webhook(listen=ut.config('listen'),
                              port=ut.config('port'),
                              url_path=ut.config('bot'),
                              cert=ut.config('cert'),
                              webhook_url=(f"https://"
                                           f"{ut.config('ip')}/"
                                           f"{ut.config('bot')}")
                              )
        updater.idle()
    else:
        print(f"File {ut.FILES['cfg']} not found.")
