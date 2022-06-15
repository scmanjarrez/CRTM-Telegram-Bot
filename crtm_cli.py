#!/usr/bin/env python3

# SPDX-License-Identifier: MIT

# Copyright (c) 2022 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

import crtm_gui as gui
import database as db
import unicodedata
import utils as ut


HELP = (
    "Esto es lo que puedo hacer por ti:"
    "\n\n"

    "❔ /menu - Interactúa con el bot mediante botones."
    "\n\n"

    "❔ /tiempo - Información sobre el tiempo."
    "\n"
    "❔ /abono <code>&lt;número&gt;</code> - Información sobre el abono "
    "transporte."
    "\n"
    "❔ /metro <code>&lt;nombre&gt;</code> - Tiempos de la estación "
    "de metro."
    "\n"
    "❔ /cercanias <code>&lt;nombre&gt;</code> - Tiempos de la estación "
    "de cercanías."
    "\n"
    "❔ /emt <code>&lt;nombre/número&gt;</code> - Tiempos de la parada "
    "de autobuses (EMT)."
    "\n"
    "❔ /interurbano <code>&lt;nombre/número&gt;</code> - Tiempos de la "
    "parada de autobuses (Interurbano)."
    "\n"
    "❔ /favoritos - Lista de favoritos."
    "\n"
    "❔ /renombrar - Renombrar un favorito."
    "\n\n"

    "❔ /ayuda - Lista de comandos."
    "\n"
    "❔ /sugerir - Enviar una sugerencia."
    "\n"
    "❔ /donar - Hacer un donativo (ko-fi)."
    "\n"
    "❔ /borrar - Elimina la información relacionada con tu cuenta."
    "\n\n"

    "❕ <b>Nota:</b> No es necesario dar el nombre completo, "
    "dame una parte y te sugeriré coincidencias."
)


def start(update, context):
    uid = ut.uid(update)
    msg = HELP
    if not db.cached(uid):
        db.add_user(uid)
        msg = f"Estupendo, ya podemos continuar.\n\n{HELP}"
    ut.send(update, msg)


def menu(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.main_menu(update)


def weather(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.weather_menu(update)


def card(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        msg = gui.CARD
        cardn = db.card(uid)
        if context.args:
            cardn = context.args[0]
        if cardn is not None:
            msg = ut.text_card(uid, cardn)
        ut.send(update, msg)


def _normalize(word):
    nfkd = unicodedata.normalize('NFKD', word)
    return u"".join([c for c in nfkd if not unicodedata.combining(c)]).lower()


def _is_int(text):
    try:
        int(text)
    except ValueError:
        return False
    return True


def times(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        msg = "Es necesario que me indiques un nombre"
        sugg = []
        cmd = update.message.text.split()[0]
        if cmd == '/metro':
            msg = f"{msg}.\n\n<b>Ejemplo</b>:\n- /metro <code>príncipe</code>"
            cmd = cmd[1:]
        elif cmd == '/cercanias':
            msg = (f"{msg}.\n\n<b>Ejemplo</b>:\n- /cercanias <code>atocha"
                   f"</code>")
            cmd = 'cerc'
        else:
            if cmd == '/emt':
                msg = (f"{msg} o número.\n\n<b>Ejemplos</b>:\n- /emt "
                       f"<code>aluche</code>\n- /emt <code>658</code>")
                cmd = cmd[1:]
            else:
                msg = (f"{msg} o número.\n\n<b>Ejemplos</b>:\n- /interurbano "
                       f"<code>aluche</code>\n- /interurbano <code>10866"
                       f"</code>")
                cmd = 'urb'
            if context.args and _is_int(context.args[0]):
                match = False
                for idx, stop_id in enumerate(ut.DATA['proc'][cmd]['ids']):
                    code = context.args[0]
                    if cmd == 'emt':
                        cmp = f'EMT_{code}'
                    else:
                        cmp = f'CRTM_8_{code}'
                    if cmp == stop_id:
                        match = True
                        break
                if match:
                    gui.bus_time(update, cmd, idx)
                    return
        if context.args:
            msg = "Estas paradas encajan con tu búsqueda"
            for word in context.args:
                for stop in ut.DATA['proc'][cmd]['names']:
                    if _normalize(word) in stop.lower():
                        index = ut.DATA['proc'][cmd]['index'][stop]
                        data = (stop, f"time_cli_{cmd}_{index}")
                        if data not in sugg:
                            sugg.append(data)
            if not sugg:
                msg = "No existen paradas con ese criterio"
        ut.send(update, msg, reply_markup=gui.markup(sugg))


def favorites(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.favorites_menu(update)


def rename(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.rename_menu(update)


def bot_help(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        ut.send(update, HELP)


def donate(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        ut.send(update,
                "Puedes comprarme un café en "
                "https://ko-fi.com/zuzumebachi 😊")


def suggest(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        if uid not in ut.STATE:
            ut.STATE[uid] = ('suggest',)
        ut.send(update,
                "Dime qué debería mejorar o añadir, haré lo posible "
                "por implementarlo.")


def text(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        if uid in ut.STATE:
            if ut.STATE[uid][0] == 'suggest':
                ut.store_suggestion(update.message.text)
                ut.send(update,
                        "He tomado nota de la sugerencia. Gracias.")
            else:
                transport, index = ut.STATE[uid][1]
                stop_id, stop = ut.transport_info(transport, index)
                db.rename_favorite(uid, transport, stop_id,
                                   update.message.text)
                ut.send(update,
                        f"El nombre de la estación/parada '{stop}' "
                        f"ahora será '{update.message.text}'")
            del ut.STATE[uid]


def remove(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        db.del_data(uid)
        msg = ("Es una pena verte marchar 😢. "
               "He borrado toda la información que tenía sobre ti.")
        ut.send(update, msg)
