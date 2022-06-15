#!/usr/bin/env python3

# SPDX-License-Identifier: MIT

# Copyright (c) 2022 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

import database as db
import utils as ut


CARD = ("Es necesario que me indiques un número.\n\n"
        "<b>Ejemplo</b>:\n- /abono <code>0010000000</code>\n\n"
        "<b>Nota</b>: <code>&lt;número&gt;</code> se compone por los "
        "3 últimos dígitos de la primera fila y los dígitos de la "
        "segunda fila.")


def _answer(update, msg=None):
    if update.callback_query is not None:
        try:
            update.callback_query.answer(msg)
        except BadRequest:
            pass


def button(buttons):
    return [InlineKeyboardButton(bt[0], callback_data=bt[1]) for bt in buttons]


def button_url(buttons):
    return [InlineKeyboardButton(bt[0], bt[1]) for bt in buttons]


def markup(buttons):
    if buttons:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(stop, callback_data=stop_id)]
             for stop, stop_id in buttons])


def main_menu(update):
    _answer(update)
    kb = [button([("🌤 Tiempo 🌤", 'weather_menu'),
                  ("💳 Abono 💳", 'card_menu')]),
          button([("🚇 Metro 🚇", 'train_menu_metro'),
                  ("🚆 Cercanías 🚆", 'train_menu_cerc')]),
          button([("🚎 EMT 🚎", 'bus_menu_emt'),
                  ("🚌 Interurbano 🚌", 'bus_menu_urb')]),
          button([("❤️ Favoritos ❤️", 'favorites_menu')])]
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, "Menú", reply_markup=InlineKeyboardMarkup(kb))


# weather_menu
def weather_menu(update):
    msg = ut.text_weather()
    _answer(update)
    kb = [button([("🔃 Actualizar 🔃", 'weather_menu')]),
          button([("« Menú", 'main_menu')])]
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, ''.join(msg), reply_markup=InlineKeyboardMarkup(kb))


# card_menu
def card_menu(update):
    uid = ut.uid(update)
    msg = CARD
    kb = []
    _answer(update)
    if db.card(uid) is not None:
        msg = ut.text_card(uid)
        kb.append(button([("🔃 Actualizar 🔃", 'card_menu')])),
    kb.append(button([("« Menú", 'main_menu')]))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, ''.join(msg), reply_markup=InlineKeyboardMarkup(kb))


# train_menu_<transport> -> line_menu_<transport>_<line>
def train_menu(update, transport):
    _answer(update)
    keys = list(ut.DATA['proc'][transport]['lines'].keys())
    kb = []
    for lines in list(ut.chunk(keys)):
        kb.append(
            button([(line, f'line_menu_{transport}_{line}')
                    for line in lines]))
    kb.append(button([("A-Z", f'line_menu_{transport}_A-Z')]))
    kb.append(button([("« Menú", 'main_menu')]))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    transl = "Metro"
    if transport == 'cerc':
        transl = "Cercanías"
    resp(update, f"Líneas de {transl}",
         reply_markup=InlineKeyboardMarkup(kb))


# line_menu_<transport>_<line> -> station_menu_<transport>_<line>_<letter>
def train_line_menu(update, transport, line):
    _answer(update)
    if line == 'A-Z':
        keys = sorted(list(ut.DATA['proc'][transport]['stops'].keys()))
    else:
        keys = list(ut.DATA['proc'][transport]['lines'][line].keys())
    kb = []
    for letters in list(ut.chunk(keys)):
        kb.append(button([(letter,
                           f'station_menu_{transport}_{line}_{letter}')
                          for letter in letters]))
    kb.append(button([("« Líneas", f'train_menu_{transport}'),
                      ("« Menú", 'main_menu')]))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, f"Estaciones de la Línea {line}",
         reply_markup=InlineKeyboardMarkup(kb))


# station_menu_<transport>_<line>_<letter> ->
# time_train_<transport>_<line>_<letter>_<index>
def train_station_menu(update, transport, line, letter):
    _answer(update)
    if line == 'A-Z':
        idxs = ut.DATA['proc'][transport]['stops'][letter]
    else:
        idxs = ut.DATA['proc'][transport]['lines'][line][letter]
    kb = []
    for idx in idxs:
        _, stop = ut.transport_info(transport, idx)
        kb.append(
            button([(stop, f'time_train_{transport}_{line}_{letter}_{idx}')]))
    kb.append(button([(f"« Línea {line}",
                       f'line_menu_{transport}_{line}'),
                      ("« Líneas", f'train_menu_{transport}'),
                      ("« Menú", 'main_menu')]))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, f"Estaciones de la Línea {line} ({letter})",
         reply_markup=InlineKeyboardMarkup(kb))


# time_train_<transport>_<line>_<letter>_<index>
def train_time(update, transport, line, letter, index):
    kb = []
    stop_id, stop = ut.transport_info(transport, index)
    msg = [f"Tiempos en estación {stop}\n\n"]
    if transport == 'metro':
        ut.text_metro(stop_id, msg)
    else:
        ut.text_cercanias(stop_id, msg)
    _answer(update)
    add_upd_button(kb, f'time_train_{transport}_{line}_{letter}_{index}')
    kb.append(button([("« Estaciones",
                       f'station_menu_{transport}_{line}_{letter}'),
                      (f"« Línea {line}", f'line_menu_{transport}_{line}'),
                      ("« Líneas", f'train_menu_{transport}'),
                      ("« Menú", 'main_menu')]))
    add_fav_button(kb, update, transport, index, stop_id)
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, ''.join(msg),
         reply_markup=InlineKeyboardMarkup(kb))


def add_upd_button(keyboard, callback_data):
    keyboard.append(button([("🔃 Actualizar 🔃", callback_data)]))


def add_fav_button(keyboard, update, transport, index, stop_id):
    uid = ut.uid(update)
    if not db.favorite_cached(uid, transport, stop_id):
        keyboard.append(button([("❤️ Guardar en Favoritos ❤️",
                                 f'fav_{uid}_{transport}_{index}')]))


# bus_menu_<transport>
def bus_menu(update, transport):
    _answer(update)
    kb = []
    kb.append(button([("« Menú", 'main_menu')]))
    msg = "Envía el nombre de la parada o el número al comando"
    if transport == 'emt':
        msg = (f"{msg} /emt.\n\n"
               f"<b>Ejemplos</b>:\n- /emt <code>aluche</code>\n"
               f"- /emt <code>658</code>")
    else:
        msg = (f"{msg} /interurbano.\n\n"
               f"<b>Ejemplos</b>:\n- /interurbano <code>aluche</code>\n"
               f"- /interurbano <code>10866</code>")
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, msg,
         reply_markup=InlineKeyboardMarkup(kb))


# time_bus_<transport>_<index>
def bus_time(update, transport, index):
    kb = []
    stop_id, stop = ut.transport_info(transport, index)
    if transport == 'emt':
        msg = [f"Tiempos en parada {stop} ("
               f"{stop_id.replace('EMT_', '')})\n\n"]
    else:
        msg = [f"Tiempos en parada {stop} ("
               f"{stop_id.replace('CRTM_8_', '')})\n\n"]
    ut.text_bus(transport, stop_id, msg)
    _answer(update)
    add_upd_button(kb, f'time_bus_{transport}_{index}')
    add_fav_button(kb, update, transport, index, stop_id)
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, ''.join(msg),
         reply_markup=InlineKeyboardMarkup(kb))


# time_cli_<transport>_<index>
def cli_time(update, transport, index):
    kb = []
    stop_id, stop = ut.transport_info(transport, index)
    msg = [f"Tiempos en estación {stop}\n\n"]
    if transport == 'metro':
        ut.text_metro(stop_id, msg)
    elif transport == 'cerc':
        ut.text_cercanias(stop_id, msg)
    else:
        if transport == 'emt':
            msg = [f"Tiempos en parada {stop} ("
                   f"{stop_id.replace('EMT_', '')})\n\n"]
        else:
            msg = [f"Tiempos en parada {stop} ("
                   f"{stop_id.replace('CRTM_8_', '')})\n\n"]
        ut.text_bus(transport, stop_id, msg)
    _answer(update)
    add_upd_button(kb, f'time_cli_{transport}_{index}')
    add_fav_button(kb, update, transport, index, stop_id)
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, ''.join(msg),
         reply_markup=InlineKeyboardMarkup(kb))


# favorites_menu
def favorites_menu(update):
    favorites = db.favorites(ut.uid(update))
    _answer(update)
    msg = "No tienes paradas/estaciones en guardadas en favoritos"
    kb = []
    if favorites:
        msg = "Estas son tus paradas/estaciones en favoritos"
        for transport, stop_id, stop in favorites:
            index = ut.index(transport, stop_id)
            kb.append(
                button(
                    [(f"{transport}: {stop}",
                      f'time_fav_{transport}_{index}')]))
    kb.append(button([("« Menú", 'main_menu')]))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, msg,
         reply_markup=InlineKeyboardMarkup(kb))


# fav_<uid>_<transport>_<index>
def add_favorite(update, uid, transport, index):
    stop_id, stop = ut.transport_info(transport, index)
    db.add_favorite(uid, transport, stop_id, stop)
    message = update.callback_query.message
    if transport == 'metro':
        text = ut.reformat(message.text)
    elif transport == 'cerc':
        text = ut.reformat_cercanias(message.text)
    else:
        text = ut.reformat(message.text)
    ut.edit(update, text,
            reply_markup=InlineKeyboardMarkup(
                message.reply_markup.inline_keyboard[:-1]))


# unfav_<uid>_<transport>_<index>
def del_favorite(update, uid, transport, index):
    stop_id, _ = ut.transport_info(transport, index)
    db.del_favorite(uid, transport, stop_id)
    favorites_menu(update)


# time_fav_<transport>_<index>
def time_favorite_menu(update, transport, index):
    kb = []
    stop_id, stop = ut.transport_info(transport, index)
    msg = [f"Tiempos en estación {stop}\n\n"]
    if transport == 'metro':
        ut.text_metro(stop_id, msg)
    elif transport == 'cerc':
        ut.text_cercanias(stop_id, msg)
    else:
        if transport == 'emt':
            msg = [f"Tiempos en parada {stop} ("
                   f"{stop_id.replace('EMT_', '')})\n\n"]
        else:
            msg = [f"Tiempos en parada {stop} ("
                   f"{stop_id.replace('CRTM_8_', '')})\n\n"]
        ut.text_bus(transport, stop_id, msg)
    _answer(update)
    add_upd_button(kb, f'time_fav_{transport}_{index}')
    kb.append(button([("« Favoritos", 'favorites_menu'),
                      ("« Menú", 'main_menu')]))
    uid = ut.uid(update)
    kb.append(button([("💔 Eliminar de Favoritos 💔",
                       f'unfav_{uid}_{transport}_{index}')]))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, ''.join(msg),
         reply_markup=InlineKeyboardMarkup(kb))


def rename_menu(update):
    favorites = db.favorites(ut.uid(update))
    _answer(update)
    msg = "No tienes estaciones/paradas en guardadas en favoritos"
    kb = []
    if favorites:
        msg = "Indícame la estación/parada que quieras renombrar"
        for transport, stop_id, stop in favorites:
            index = ut.index(transport, stop_id)
            kb.append(
                button(
                    [(f"{transport}: {stop}",
                      f'rename_fav_{transport}_{index}')]))
    kb.append(button([("« Menú", 'main_menu')]))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update, msg,
         reply_markup=InlineKeyboardMarkup(kb))


# rename_fav_<transport>_<index>
def rename_favorite(update, transport, index):
    uid = ut.uid(update)
    ut.STATE[uid] = ('rename', (transport, index))
    resp = ut.send
    if update.callback_query is not None:
        resp = ut.edit
    resp(update,
         "De acuerdo, indícame el nuevo nombre de la estación/parada",
         reply_markup=None)
