#!/usr/bin/env python3

# SPDX-License-Identifier: MIT

# Copyright (c) 2022-2026 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

import traceback

import crtm.database as db
import crtm.gui as gui
import crtm.utils as ut
from telegram.error import BadRequest


HELP_CMD = {
    "start": "Inicia el bot (obligatorio la primera vez)",
    "menu": "Menú interactivo",
    "tiempo": "Información sobre el tiempo",
    "bici": "Estadísticas de la estación de bicimad",
    "metro": "Tiempos de la estación de metro",
    "cercanias": "Tiempos de la estación de cercanías",
    "emt": "Tiempos de la parada de autobuses",
    "interurbano": "Tiempos de la parada de interurbano",
    "favoritos": "Lista de favoritos",
    "renombrar": "Renombrar un favorito",
    "ayuda": "Lista de comandos",
    "sugerir": "Enviar una sugerencia",
    "informar": "Informar sobre un problema",
    "donar": "Hacer un donativo (ko-fi)",
    "borrar": "Elimina toda la información sobre ti",
}
HELP = (
    f"Esto es lo que puedo hacer por ti:\n\n"
    f"❔ /menu - {HELP_CMD['menu']}\n\n"
    f"❔ /tiempo - {HELP_CMD['tiempo']}\n"
    f"❔ /bici <code>&lt;nombre/número&gt;</code> - {HELP_CMD['bici']}\n"
    f"❔ /metro <code>&lt;nombre&gt;</code> - {HELP_CMD['metro']}\n"
    f"❔ /cercanias <code>&lt;nombre&gt;</code> - {HELP_CMD['cercanias']}\n"
    f"❔ /emt <code>&lt;nombre/número&gt;</code> - {HELP_CMD['emt']}\n"
    f"❔ /interurbano <code>&lt;nombre/número&gt;</code> - "
    f"{HELP_CMD['interurbano']}\n"
    f"❕ <b>Nota:</b> Sólo debes dar una parte del nombre y "
    f"te sugeriré coincidencias.\n\n"
    f"❔ /favoritos - {HELP_CMD['favoritos']}\n"
    f"❔ /renombrar - {HELP_CMD['renombrar']}\n\n"
    f"❔ /start - {HELP_CMD['start']}\n"
    f"❔ /ayuda - {HELP_CMD['ayuda']}\n"
    f"❔ /sugerir - {HELP_CMD['sugerir']}\n"
    f"❔ /informar - {HELP_CMD['informar']}\n"
    f"❔ /donar - {HELP_CMD['donar']}\n"
    f"❔ /borrar - {HELP_CMD['borrar']}\n"
    f"❕ <b>Nota:</b> También puedes usarme en modo inline de esta forma: "
    f"@crtmadrid_bot <code>transporte</code> <code>texto</code>.\n"
    f"- <b>transporte</b>: puede ser bici, metro, cercanias, emt o interurbano\n"
    f"- <b>texto</b>: puede ser un nombre o número de parada en caso de "
    f"bici, emt o interubano"
)


def start(update, _):
    uid = ut.uid(update)
    msg = HELP
    if not db.cached(uid):
        db.add_user(uid)
        msg = f"Estupendo, ya podemos continuar.\n\n{HELP}"
    ut.send(update, msg)


def menu(update, _):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.main_menu(update)


def weather(update, _):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.weather_menu(update)


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
            msg = f"{msg}.\n\n<b>Ejemplo</b>:\n- /cercanias <code>atocha</code>"
            cmd = "cerc"
        else:
            if cmd == "/bici":
                msg = (
                    f"{msg} o número.\n\n<b>Ejemplos</b>:\n- /bici "
                    f"<code>casal</code>\n- /bici <code>77</code>"
                )
                cmd = cmd[1:]
            elif cmd == "/emt":
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
                match, index = ut.stopnumber_match(
                    cmd, context.args[0]
                )
                if match:
                    gui.bus_time(update, cmd, index)
                    return
        if context.args:
            msg = "Estas paradas encajan con tu búsqueda"
            suggs = ut.stopname_matches(cmd, context.args)
            if not suggs:
                msg = "No existen paradas con ese criterio"
        ut.send(update, msg, reply_markup=gui.markup(suggs))


def favorites(update, _):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.favorites_menu(update)


def rename(update, _):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        gui.rename_menu(update)


def bot_help(update, _):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        ut.send(update, HELP)


def donate(update, _):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        ut.send(
            update,
            "Puedes comprarme un café en https://ko-fi.com/zuzumebachi 😊",
        )


def suggest(update, _):
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

def report(update, _):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        if uid not in ut.STATE:
            ut.STATE[uid] = ("report",)
        ut.send(
            update,
            "Por favor, indícame el problema y los pasos para reproducirlo.",
        )


def text(update, context):
    uid = ut.uid(update)
    if not db.cached(uid):
        ut.not_started(update)
    else:
        if uid in ut.STATE:
            if ut.STATE[uid][0] in ["suggest", "report"]:
                word = "de la sugerencia"
                word2 = "Suggestion"
                if ut.STATE[uid][0] == "report":
                    word = "del informe"
                    word2 = "Report"
                msg = f"He tomado nota {word}. Gracias."
                ut.send_bot(context.bot, ut.admin("id"),
                            f"{word2}: {update.message.text}")
                ut.store_message(update.message.text,
                                 rep=ut.STATE[uid][0] == "report")
                ut.send(update, msg)
            else:
                transport, index = ut.STATE[uid][1]
                stop, stop_id = ut.transport_info(transport, index)
                db.rename_favorite(
                    uid, transport, stop_id, update.message.text
                )
                ut.send(
                    update,
                    f"El nombre de la estación/parada '{stop}' "
                    f"ahora será '{update.message.text}'",
                )
            del ut.STATE[uid]


def remove(update, _):
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
    msg, _ = ut.text_transport(args[-2], args[-1])
    gui._answer(update)
    gui.add_upd_button(kb, callback_data)
    try:
        context.bot.edit_message_text(
            "".join(msg),
            inline_message_id=msg_id,
            parse_mode=ut.ParseMode.HTML,
            reply_markup=gui.markup(
                [("🔃 Actualizar 🔃", callback_data)]
            ),
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
    inline_text(
        update, context, chosen.inline_message_id, chosen.result_id
    )


def inline_query(update, _):
    query = update.inline_query.query
    if query == "":
        return
    args = query.split()
    cmd = ut.normalize(args[0]).lower()
    results = []
    if len(args) > 1:
        if cmd in ut.CMD_TRANS:
            transport, stype = ut.CMD_TRANS[cmd]
            if transport == "bici":
                msg = f"estadísticas de {stype}"
            else:
                msg = f"tiempos en {stype}"
            if ut.is_bus(transport) and ut.is_int(args[1]):
                match, index = ut.stopnumber_match(transport, args[1])
                if match:
                    stop, stop_id = ut.transport_info(
                        transport, index
                    )
                    stop_id = stop_id.split("_")[-1]
                    results.append(
                        ut.result(
                            transport,
                            f"time_inline_{transport}_{index}",
                            f"{msg} {stop} ({stop_id})",
                        )
                    )
            else:
                matches = ut.stopname_matches(
                    transport, args[1:], inline=True
                )
                for match in matches:
                    results.append(
                        ut.result(
                            transport, match[1], f"{msg} {match[0]}"
                        )
                    )
        else:
            return
    else:
        return
    update.inline_query.answer(results[:50])


def privacy(update, _):
    ut.send(
        update,
        "This bot collects and stores the <code>USER ID</code> "
        "to function correctly. The <code>USER ID</code> is used exclusively "
        "for storing user's favorite stations. It is not used for any other "
        "purposes. For those interested in auditing the bot's code, the "
        "source code is available at: "
        "https://github.com/scmanjarrez/CRTM-Telegram-Bot. "
        "If you do not consent to this policy, you may use the /stop command "
        "to have your information removed from the bot's records."
    )
