#!/usr/bin/env python3

# SPDX-License-Identifier: MIT

# Copyright (c) 2022-2023 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

import traceback

import crtm_gui as gui
import database as db
import utils as ut
from telegram.error import BadRequest


HELP = (
    "Esto es lo que puedo hacer por ti:"
    "\n\n"
    "❔ /menu - Interactúa con el bot mediante botones."
    "\n\n"
    "❔ /tiempo - Información sobre el tiempo."
    "\n"
    "❔ /abono <code>&lt;número&gt;</code> - Información sobre el abono "
    "transporte. Elimínalo enviando -1."
    "\n"
    "❔ /guardar_abono - Activa/desactiva el guardado del abono en la "
    "base de datos. Desactivado por defecto."
    "\n\n"
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
    "\n\n"
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
    "dame una parte y te sugeriré coincidencias.\n\n"
    ""
    "❕ <b>Nota2:</b> Si no deseas usar interactuar con el bot, también "
    "puedes usarme en modo inline de esta forma:\n@crtmadrid_bot "
    "<code>[metro|cercanias|emt|interurbano]</code> "
    "<code>[nombre|número]</code>."
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
            if cardn == "-1":
                db.del_card(uid)
                msg = "He eliminado la información sobre tu abono"
            else:
                msg = ut.text_card(uid, cardn)
        ut.send(update, msg)


def save_card(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        if db.save_card(uid):
            msg = "Se ha desactivado el guardado del abono en la base de datos"
        else:
            msg = "Se ha activado el guardado del abono en la base de datos"
        db.toggle_card(uid)
        ut.send(update, msg)


def times(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        msg = "Es necesario que me indiques un nombre"
        suggs = []
        cmd = update.message.text.split()[0]
        if cmd == "/metro":
            msg = f"{msg}.\n\n<b>Ejemplo</b>:\n- /metro <code>príncipe</code>"
            cmd = cmd[1:]
        elif cmd == "/cercanias":
            msg = (
                f"{msg}.\n\n<b>Ejemplo</b>:\n- /cercanias <code>atocha"
                f"</code>"
            )
            cmd = "cerc"
        else:
            if cmd == "/emt":
                msg = (
                    f"{msg} o número.\n\n<b>Ejemplos</b>:\n- /emt "
                    f"<code>aluche</code>\n- /emt <code>658</code>"
                )
                cmd = cmd[1:]
            else:
                msg = (
                    f"{msg} o número.\n\n<b>Ejemplos</b>:\n- /interurbano "
                    f"<code>aluche</code>\n- /interurbano <code>10866"
                    f"</code>"
                )
                cmd = "urb"
            if context.args and ut.is_int(context.args[0]):
                match, index = ut.stopnumber_match(cmd, context.args[0])
                if match:
                    gui.bus_time(update, cmd, index)
                    return
        if context.args:
            msg = "Estas paradas encajan con tu búsqueda"
            suggs = ut.stopname_matches(cmd, context.args)
            if not suggs:
                msg = "No existen paradas con ese criterio"
        ut.send(update, msg, reply_markup=gui.markup(suggs))


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
        ut.send(
            update,
            "Puedes comprarme un café en https://ko-fi.com/zuzumebachi 😊",
        )


def suggest(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        if uid not in ut.STATE:
            ut.STATE[uid] = ("suggest",)
        ut.send(
            update,
            "Dime qué debería mejorar o añadir al bot, haré lo posible "
            "por implementarlo.",
        )


def text(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        if uid in ut.STATE:
            if ut.STATE[uid][0] == "suggest":
                ut.store_suggestion(update.message.text)
                ut.send(update, "He tomado nota de la sugerencia. Gracias.")
            else:
                transport, index = ut.STATE[uid][1]
                stop_id, stop = ut.transport_info(transport, index)
                db.rename_favorite(
                    uid, transport, stop_id, update.message.text
                )
                ut.send(
                    update,
                    f"El nombre de la estación/parada '{stop}' "
                    f"ahora será '{update.message.text}'",
                )
            del ut.STATE[uid]


def remove(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        db.del_data(uid)
        msg = (
            "Es una pena verte marchar 😢. "
            "He borrado toda la información que tenía sobre ti."
        )
        ut.send(update, msg)


def inline_text(update, context, msg_id, callback_data):
    kb = []
    args = callback_data.split("_")
    msg, stop_id = ut.text_transport(args[-2], args[-1])
    gui._answer(update)
    gui.add_upd_button(kb, callback_data)
    try:
        context.bot.edit_message_text(
            "".join(msg),
            inline_message_id=msg_id,
            parse_mode=ut.ParseMode.HTML,
            reply_markup=gui.markup([("🔃 Actualizar 🔃", callback_data)]),
        )
    except BadRequest as br:
        if not str(br).startswith("Message is not modified:"):
            print(
                f"***  Exception caught in edit "
                f"({update.effective_message.chat.id}): ",
                br,
            )
            traceback.print_stack()


def inline_message(update, context):
    chosen = update.chosen_inline_result
    inline_text(update, context, chosen.inline_message_id, chosen.result_id)


def inline_query(update, context):
    query = update.inline_query.query
    if query == "":
        return
    args = query.split()
    cmd = ut.normalize(args[0]).lower()
    results = []
    if len(args) > 1:
        if cmd in ut.CMD_TRANS:
            transport, stype = ut.CMD_TRANS[cmd]
            msg = f"tiempos en {stype}"
            if ut.is_bus(transport) and ut.is_int(args[1]):
                match, index = ut.stopnumber_match(transport, args[1])
                if match:
                    stop_id, stop = ut.transport_info(transport, index)
                    stop_id = stop_id.split("_")[-1]
                    results.append(
                        ut.result(
                            transport,
                            f"time_inline_{transport}_{index}",
                            f"{msg} {stop} ({stop_id})",
                        )
                    )
            else:
                matches = ut.stopname_matches(transport, args[1:], inline=True)
                for match in matches:
                    results.append(
                        ut.result(transport, match[1], f"{msg} {match[0]}")
                    )
        else:
            return
    else:
        return
    update.inline_query.answer(results[:50])
