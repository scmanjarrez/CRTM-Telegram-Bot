#!/usr/bin/env python3

# SPDX-License-Identifier: MIT

# Copyright (c) 2022-2023 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

from telegram.ext import (CallbackQueryHandler, ChosenInlineResultHandler,
                          CommandHandler, Filters, InlineQueryHandler,
                          MessageHandler, Updater)

import crtm_cli as cli
import crtm_gui as gui
import database as db
import utils as ut
import logging
import os


def button_handler(update, context):
    query = update.callback_query
    if query.inline_message_id is not None:
        cli.inline_text(update, context,
                        query.inline_message_id, query.data)
    else:
        uid = ut.uid(update)
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
            elif query.data.startswith('fav'):
                args = query.data.split('_')
                gui.add_favorite(update, args[-3], args[-2], args[-1])
            elif query.data.startswith('unfav'):
                args = query.data.split('_')
                gui.del_favorite(update, args[-3], args[-2], args[-1])
            elif query.data.startswith('time_fav'):
                args = query.data.split('_')
                gui.time_favorite_menu(update, args[-2], args[-1])
            elif query.data.startswith('rename_fav'):
                args = query.data.split('_')
                gui.rename_favorite(update, args[-2], args[-1])


def setup_handlers(dispatch, job_queue):
    start_handler = CommandHandler('start', cli.start,
                                   filters=~Filters.update.edited_message)
    dispatch.add_handler(start_handler)

    menu_handler = CommandHandler('menu', cli.menu,
                                  filters=~Filters.update.edited_message)
    dispatch.add_handler(menu_handler)

    weather_handler = CommandHandler('tiempo', cli.weather,
                                     filters=~Filters.update.edited_message)
    dispatch.add_handler(weather_handler)

    card_handler = CommandHandler('abono', cli.card,
                                  filters=~Filters.update.edited_message)
    dispatch.add_handler(card_handler)

    save_handler = CommandHandler('guardar_abono', cli.save_card,
                                  filters=~Filters.update.edited_message)
    dispatch.add_handler(save_handler)

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

    rename_handler = CommandHandler('renombrar', cli.rename,
                                    filters=~Filters.update.edited_message)
    dispatch.add_handler(rename_handler)

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
        Filters.text & ~Filters.update.edited_message, cli.text)
    dispatch.add_handler(text_handler)

    dispatch.add_handler(CallbackQueryHandler(button_handler))

    dispatcher.add_handler(InlineQueryHandler(cli.inline_query))

    dispatcher.add_handler(ChosenInlineResultHandler(cli.inline_message))


if __name__ == '__main__':
    logging.basicConfig(format=('%(asctime)s - %(name)s - '
                                '%(levelname)s - %(message)s'),
                        level=logging.INFO)

    if os.path.isfile(ut.FILES['cfg']):
        db.setup_db()
        ut.load_config()

        updater = Updater(token=ut.setting('token'), use_context=True)
        dispatcher = updater.dispatcher
        setup_handlers(dispatcher, updater.job_queue)

        ut.update_data(None)
        ut.downloader_daily(updater.job_queue)

        updater.start_webhook(listen=ut.setting('listen'),
                              port=ut.setting('port'),
                              url_path=ut.setting('token'),
                              cert=ut.setting('cert'),
                              webhook_url=(f"https://"
                                           f"{ut.setting('ip')}/"
                                           f"{ut.setting('token')}")
                              )
        # updater.start_polling()
        updater.idle()
    else:
        print(f"File {ut.FILES['cfg']} not found.")
