#!/usr/bin/env python3
# SPDX-License-Identifier: MIT


# Copyright (c) 2022-2023 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

import datetime
import json
import logging
import re
import traceback
import unicodedata
from pathlib import Path

import crtm_gui as gui
import database as db

import endpoints as end  # not uploaded for privacy reasons
import pytz
import requests as req
from bs4 import BeautifulSoup
from dateutil import parser as ps
from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    ParseMode,
)
from telegram.error import BadRequest, Unauthorized


STATE = {}
KB_WIDTH = 4
LOGO = (
    "https://raw.githubusercontent.com/"
    "scmanjarrez/CRTM-Telegram-Bot/master/logos"
)
RE = {
    "code": re.compile(r"4__(\d+)___"),
    "line": re.compile(r"(Línea) (.*):"),
    "orig": re.compile(r"(Origen:) (.*)"),
    "dest": re.compile(r"(Destino:) (.*)"),
    "time": re.compile(r"(Tiempo\(s\):) (.*)"),
    "type": re.compile(r"^(\w+):$"),
}
CMD_TRANS = {
    "metro": ("metro", "estación"),
    "cercanias": ("cerc", "estación"),
    "emt": ("emt", "parada"),
    "interurbano": ("urb", "parada"),
    "types": {"train": ("metro", "cerc"), "bus": ("emt", "urb")},
}
FILES = {
    "cfg": ".config.json",
    "token": ".token",
    "metro": "data/metro.json",
    "cerc": "data/cercanias.json",
    "emt": "data/emt.json",
    "urb": "data/interurbanos.json",
}
CONFIG = {}
DATA = {}


def _debug_request(req):
    print(req.request.url, req.request.body, req.request.headers)


def load_config():
    global CONFIG
    with open(FILES["cfg"]) as f:
        CONFIG = json.load(f)
    try:
        logging.getLogger().setLevel(setting("log_level").upper())
    except KeyError:
        pass


def setting(key):
    return CONFIG["settings"][key]


def api(key):
    return CONFIG["api"][key]


def download_api_data():
    emt_path = Path(FILES["emt"])
    emt_path.parent.mkdir(exist_ok=True)
    get = req.get(
        f'{end.URL["cloud"]}{end.END["raw_emt"]}',
        params={"a": "EMT", "t": 3},
        headers=end.headers(),
    )
    if get.status_code != 200:
        return
    data = parse_api_data(json.loads(get.text))
    with emt_path.open("w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    urb_path = Path(FILES["urb"])
    get = req.get(
        f'{end.URL["cloud"]}{end.END["raw_urb"]}',
        params={"a": "CRTM", "t": 3},
        headers=end.headers(),
    )
    if get.status_code != 200:
        return
    data = parse_api_data(json.loads(get.text))
    with urb_path.open("w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    metro_path = Path(FILES["metro"])
    get = req.get(
        f'{end.URL["cloud"]}{end.END["raw_metro"]}',
        params={"a": "CRTM", "t": 0},
        headers=end.headers(),
    )
    if get.status_code != 200:
        return
    ml_data = parse_api_data(json.loads(get.text))
    get = req.get(
        f'{end.URL["cloud"]}{end.END["raw_metro"]}',
        params={"a": "CRTM", "t": 1},
        headers=end.headers(),
    )
    if get.status_code != 200:
        return
    data = parse_api_data(json.loads(get.text), ml_data)
    with metro_path.open("w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def parse_api_data(data, fill=None):
    names = fill
    if names is None:
        names = {"station": {}, "line": {}}
    for el in data["elements"]:
        if el["r"]["n"] not in names["line"]:
            names["line"][el["r"]["i"]] = {}
            names["line"][el["r"]["i"]]["id"] = el["r"]["h"]
            names["line"][el["r"]["i"]]["name"] = el["r"]["n"]
        for sts in el["sts"]:
            if sts["i"] not in names["station"]:
                names["station"][sts["i"]] = {}
                names["station"][sts["i"]]["name"] = sts["n"]
                names["station"][sts["i"]]["lineIds"] = data["uiStopIndexes"][
                    sts["i"]
                ]
    return names


def load_data():
    download_api_data()
    with open(FILES["cerc"], "r") as f:
        DATA["raw"]["cerc"] = json.load(f)
    with open(FILES["metro"], "r") as f:
        DATA["raw"]["metro"] = json.load(f)
    with open(FILES["emt"], "r") as f:
        DATA["raw"]["emt"] = json.load(f)
    with open(FILES["urb"], "r") as f:
        DATA["raw"]["urb"] = json.load(f)


def train_lines():
    for idx, stop in enumerate(DATA["raw"]["cerc"]):
        idname = "id"
        DATA["proc"]["cerc"]["index"][stop[idname]] = idx
        DATA["proc"]["cerc"]["names"].append(stop["name"])
        DATA["proc"]["cerc"]["ids"].append(stop[idname])

        first = stop["name"][0]
        if first not in DATA["proc"]["cerc"]["stops"]:
            DATA["proc"]["cerc"]["stops"][first] = []
        DATA["proc"]["cerc"]["stops"][first].append(idx)
        for line in stop["lineIds"]:
            if first not in DATA["proc"]["cerc"]["lines"][line]:
                DATA["proc"]["cerc"]["lines"][line][first] = []
            DATA["proc"]["cerc"]["lines"][line][first].append(idx)


def transport_lines(transport):
    for idx, info in enumerate(DATA["raw"][transport]["station"].items()):
        DATA["proc"][transport]["index"][info[0]] = idx
        DATA["proc"][transport]["names"].append(info[1]["name"])
        DATA["proc"][transport]["ids"].append(info[0])


def token():
    if DATA["token"] is None:
        try:
            with open(FILES["token"], "r+") as f:
                DATA["token"] = f.read()
        except FileNotFoundError:
            DATA["token"] = "null"
    post = req.post(
        f'{end.URL["token"]}{end.END["info"]}',
        params={"key": api("cloud")},
        data={"idToken": DATA["token"]},
        headers=end.headers("register"),
    )
    if post.status_code == 400:
        post = req.post(
            f'{end.URL["token"]}{end.END["sign"]}',
            params={"key": api("cloud")},
            headers=end.headers("register"),
        )
        data = json.loads(post.text)
        DATA["token"] = data["idToken"]
        with open(FILES["token"], "w") as f:
            f.write(DATA["token"])
    return DATA["token"]


def uid(update):
    return update.effective_message.chat.id


def blocked(uid):
    db.del_user(uid)


def send(update, msg, quote=True, reply_markup=None, disable_preview=True):
    try:
        return update.message.reply_html(
            msg,
            quote=quote,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_preview,
        )
    except Unauthorized:
        blocked(update.effective_message.chat.id)


def send_bot(bot, uid, msg, reply_markup=None, disable_preview=True):
    try:
        return bot.send_message(
            uid,
            msg,
            ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_preview,
        )
    except Unauthorized:
        blocked(uid)


def edit(update, msg, reply_markup, disable_preview=True):
    try:
        update.callback_query.edit_message_text(
            msg,
            ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_preview,
        )
    except BadRequest as br:
        if not str(br).startswith("Message is not modified:"):
            print(
                f"***  Exception caught in edit "
                f"({update.effective_message.chat.id}): ",
                br,
            )
            traceback.print_stack()


def _msg_start(update):
    return "Es necesario iniciar el bot con /start antes de continuar."


def not_started(update):
    msg = _msg_start(update)
    send(update, msg)


def not_started_gui(update):
    msg = _msg_start(update)
    edit(update, msg, None)


def weather():
    get = req.get(
        f'{end.URL["weather"]}',
        params={"lat": 40.49, "lng": -3.68, "appId": "mad", "lang": "es"},
        headers=end.headers(),
    )
    data = json.loads(get.text)
    info = {
        "summ": data["nowData"]["summary"],
        "temp": f"{data['nowData']['temperature']:.1f} ºC",
        "hum": f"{round(data['nowData']['humidity'])} %",
        "rain": f"{round(data['nowData']['precipProbability']*100)} %",
    }
    return info


def card(uid, cardn=None):
    if cardn is None:
        cardn = db.card(uid)
    get = req.get(
        f'{end.URL["cloud"]}{end.END["card"]}',
        params={"cardNumber": f"{cardn}"},
        headers=end.headers(),
    )
    data = json.loads(get.text)
    recharge = False
    for dt in data["ctmTitles"]:
        if dt["num"] == "1":
            if "data" not in dt and "carga" not in dt:
                return None
            cardinfo = dt["data"]
            if "recarga" in dt:
                cardcharge = dt["recarga"]["data"]
                recharge = True
            else:
                cardcharge = dt["carga"]["data"]
            if db.save_card(uid):
                db.add_card(uid, cardn)
    info = {}
    for ci in cardinfo:
        if ci["name"] == "ContractName":
            info["type"] = ci["value"]
    tags = {
        "firstl_date": ("ChargeFirstUseDate", "RechargeFirstUseDate"),
        "first_date": (
            "AccessEventInFirstPayDateCe",
            "AccessEventInFirstPayDateRrge",
        ),
        "last_date": ("ChargeEndDate", "RechargeEndDate"),
    }
    idx = 0
    if recharge:
        idx = 1
    for cc in cardcharge:
        for tag in tags:
            if cc["name"] == tags[tag][idx]:
                info[tag] = cc["value"]
    return info


def _metro_time(ref_time, next_time):
    next = (ps.parse(next_time) - ps.parse(ref_time)).seconds // 60 - 1
    if next < 1:
        next = "Llegando"
    return str(next)


def cercanias(stop_id):
    try:
        get = req.get(
            end.URL["adif"],
            params={
                "station": stop_id,
                "dest": "",
                "date": "",
                "previous": 1,
                "showCercanias": "true",
                "showOtros": "false",
            },
            headers=end.headers("adif"),
            timeout=15,
        )
    except req.exceptions.ReadTimeout:
        return None
    else:
        soup = BeautifulSoup(get.text, "html.parser")
        data = [
            [
                [el.text.strip() for el in row.select("td")]
                for row in plan.select("tr.recent-even, tr.recent-odd")
            ]
            for plan in soup.select("table#plan-table")
        ]
        info = {}
        for idy, times in enumerate(data):
            if times:
                if DATA["idx"]["cerc"][idy] not in info:
                    info[DATA["idx"]["cerc"][idy]] = {}
                for tm in times:
                    if tm[1] not in info[DATA["idx"]["cerc"][idy]]:
                        info[DATA["idx"]["cerc"][idy]][tm[1]] = ["", []]
                    info[DATA["idx"]["cerc"][idy]][tm[1]][0] = tm[3]
                    info[DATA["idx"]["cerc"][idy]][tm[1]][1].append(
                        (
                            tm[0] if tm[0] else "Llegando",
                            f"Vía {tm[4]}" if tm[4] else "",
                        )
                    )
        return info


def real_time(transport, stop_id):
    try:
        get = req.get(
            f'{end.URL["cloud"]}{end.END[transport]}',
            params={
                "stopId": stop_id,
                "type": 3 if transport != "metro" else 1,
            },
            headers=end.headers(),
            timeout=15,
        )
    except req.exceptions.ReadTimeout:
        return None
    else:
        if get.text in (
            "Rate exceeded.",
            "Error: could not handle the request\n",
        ):
            return None
        data = json.loads(get.text)
        if "code" in data:
            return None
        info = {}
        for bs in data["rtl"]:
            sec = [
                str(binfo["s"] // 60) if binfo["s"] > 60 else "Llegando"
                for binfo in bs["l"]
            ]
            bid = DATA["raw"][transport]["line"][bs["r"]]["id"]
            if transport == "metro":
                if bid not in info:
                    info[bid] = []
                tmp = {}
                tmp["name"] = bs["h"]
                tmp["times"] = sec
                info[bid].append(tmp)
            else:
                info[bid] = {}
                info[bid]["name"] = bs["h"]
                info[bid]["times"] = sec
        return info


def transport_info(transport, index):
    return (
        DATA["proc"][transport]["ids"][int(index)],
        DATA["proc"][transport]["names"][int(index)],
    )


def chunk(lst):
    for idx in range(0, len(lst), KB_WIDTH):
        yield lst[idx : idx + KB_WIDTH]


def reformat(text):
    text = RE["line"].sub(r"<b>\1 \2</b>:", text)
    text = RE["dest"].sub(r"\1 <code>\2</code>", text)
    text = RE["time"].sub(r"\1 <code>\2</code>", text)
    return text


def reformat_cercanias(text):
    text = text.replace("Llegadas", "<b>Llegadas</b>")
    text = text.replace("Salidas", "<b>Salidas</b>")
    text = RE["orig"].sub(r"\1 <code>\2</code>", text)
    text = RE["dest"].sub(r"\1 <code>\2</code>", text)
    text = RE["time"].sub(r"\1 <code>\2</code>", text)
    return text


def text_weather():
    data = weather()
    return [
        f"- <b>Tiempo</b>: <code>{data['summ']}</code>\n",
        f"- <b>Temperatura</b>: <code>{data['temp']}</code>\n",
        f"- <b>Humedad</b>: <code>{data['hum']}</code>\n",
        f"- <b>Probabilidad de lluvia</b>: "
        f"<code>{data['rain']}</code>\n\n",
    ]


def text_card(uid, cardn=None):
    data = card(uid, cardn)
    msg = "Número de tarjeta inválido"
    if data is not None:
        msg = (
            f"- <b>Tarjeta</b>: <code>{data['type']}</code>\n"
            f"- <b>Fecha límite primer uso</b>: "
            f"<code>{data['firstl_date']}</code>\n"
            f"- <b>Primer uso</b>: "
            f"<code>{data['first_date']}</code>\n"
            f"- <b>Caducidad</b>: "
            f"<code>{data['last_date']}</code>\n\n"
            f"<b>Nota</b>: La validez de la carga se extenderá "
            f"hasta las 5 AM del día siguiente."
        )
    return msg


def text_metro(stop, stop_id):
    msg = [f"Tiempos en estación {stop}\n\n"]
    data = real_time("metro", stop_id)
    if data is not None:
        if data:
            for line in data:
                msg.append(f"<b>Línea {line}:</b>\n")
                for drct in data[line]:
                    msg.append(
                        f"- Destino: " f"<code>{drct['name']}</code>" f"\n"
                    )
                    msg.append(
                        f"- Tiempo(s): "
                        f"<code>{', '.join(drct['times'])}"
                        f"</code>"
                        f"\n\n"
                    )
        else:
            msg.append("<b>No hay tiempos disponibles.</b>")
    else:
        msg.append(
            "<b>Debido a un error en el servicio de metro "
            "no es posible obtener información en estos momentos.</b>"
        )
    return msg


def text_cercanias(stop, stop_id):
    msg = [f"Tiempos en estación {stop}\n\n"]
    data = cercanias(stop_id)
    if data is not None:
        if data:
            for dtype in data:
                msg.append(f"<b>{dtype.capitalize()}:</b>\n")
                for direc in data[dtype]:
                    line = "{}".format(
                        f" ({data[dtype][direc][0]})"
                        if data[dtype][direc][0]
                        else ""
                    )
                    times = [
                        "{}{}".format(tm[0], f" ({tm[1]})" if tm[1] else "")
                        for tm in data[dtype][direc][1]
                    ]
                    msg.append(
                        f"- {'Origen' if dtype == 'llegadas' else 'Destino'}: "
                        f"<code>{direc}{line}</code>"
                        f"\n"
                    )
                    msg.append(
                        f"- Tiempo(s): "
                        f"<code>{', '.join(times)}</code>"
                        f"\n\n"
                    )
        else:
            msg.append("<b>No hay tiempos disponibles.</b>")
    else:
        msg.append(
            "<b>Debido a un error en el servicio de renfe "
            "no es posible obtener información en estos momentos.</b>"
        )
    return msg


def text_bus(transport, stop, stop_id):
    prefix = "EMT_"
    if transport == "urb":
        prefix = "CRTM_8_"
    msg = [f"Tiempos en parada {stop} ({stop_id.replace(prefix, '')})\n\n"]
    data = real_time(transport, stop_id)
    if data is not None:
        if data:
            for line in data:
                msg.append(f"<b>Línea {line}:</b>\n")
                msg.append(
                    f"- Destino: " f"<code>{data[line]['name']}</code>" f"\n"
                )
                msg.append(
                    f"- Tiempo(s): "
                    f"<code>{', '.join(data[line]['times'])}"
                    f"</code>"
                    f"\n\n"
                )
        else:
            msg.append("<b>No hay tiempos disponibles.</b>")
    else:
        msg.append(
            "<b>Debido a un error en el servicio de EMT "
            "no es posible obtener información en estos momentos.</b>"
        )
    return msg


def index(transport, stop_id):
    return DATA["proc"][transport]["index"][stop_id]


def store_suggestion(text):
    with open("suggestions.txt", "a") as f:
        f.write(f"{text}\n\n")


def normalize(word):
    nfkd = unicodedata.normalize("NFKD", word)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper()


def is_int(text):
    try:
        int(text)
    except ValueError:
        return False
    return True


def bus_id(transport, code):
    bid = f"EMT_{code}"
    if transport == "urb":
        bid = f"CRTM_8_{code}"
    return bid


def stop_data(transport, index, inline=False):
    stop_id, stop = transport_info(transport, index)
    prefix = "time_cli"
    if inline:
        prefix = "time_inline"
    if transport == "emt":
        stop = f"{stop} ({stop_id.replace('EMT_', '')})"
    elif transport == "urb":
        stop = f"{stop} ({stop_id.replace('CRTM_8_', '')})"
    return (stop, f"{prefix}_{transport}_{index}")


def stopname_matches(transport, stopnames, inline=False):
    stops = list(enumerate(DATA["proc"][transport]["names"]))
    for word in stopnames:
        stops = [
            (index, stop)
            for index, stop in stops
            if normalize(word) in normalize(stop)
        ]
    return [stop_data(transport, index, inline) for index, _ in stops]


def stopnumber_match(transport, stopnumber):
    match = False
    for idx, stop_id in enumerate(DATA["proc"][transport]["ids"]):
        cmp = bus_id(transport, stopnumber)
        if cmp == stop_id:
            match = True
            break
    return match, idx


def text_transport(transport, index):
    stop_id, stop = transport_info(transport, index)
    if transport == "metro":
        msg = text_metro(stop, stop_id)
    elif transport == "cerc":
        msg = text_cercanias(stop, stop_id)
    else:
        msg = text_bus(transport, stop, stop_id)
    return msg, stop_id


def result(transport, rid, msg):
    return InlineQueryResultArticle(
        id=rid,
        title=msg.capitalize(),
        input_message_content=InputTextMessageContent(f"Recopilando {msg}"),
        reply_markup=gui.markup([("🔃 Actualizar 🔃", rid)]),
        thumb_url=f"{LOGO}/{transport}.png",
        thumb_height=48,
        thumb_width=48,
    )


def is_bus(transport):
    return transport in CMD_TRANS["types"]["bus"]


def update_data(context):
    global DATA
    DATA = {
        "cfg": None,
        "token": None,
        "raw": {
            "metro": None,
            "cerc": None,
            "emt": None,
            "urb": None,
        },
        "idx": {
            "metro": {"1": "Sentido Horario", "2": "Sentido Antihorario"},
            "cerc": {0: "salidas", 1: "llegadas"},
        },
        "proc": {
            "metro": {
                "lines": {
                    "1": {},
                    "2": {},
                    "3": {},
                    "4": {},
                    "5": {},
                    "6": {},
                    "7": {},
                    "8": {},
                    "9": {},
                    "10": {},
                    "11": {},
                    "12": {},
                    "R": {},
                },
                "ban": ["13", "14", "15"],
                "stops": {},
                "index": {},
                "names": [],
                "ids": [],
            },
            "cerc": {
                "lines": {
                    "C1": {},
                    "C2": {},
                    "C3": {},
                    "C4": {},
                    "C5": {},
                    "C7": {},
                    "C8": {},
                    "C9": {},
                    "C10": {},
                },
                "stops": {},
                "index": {},
                "names": [],
                "ids": [],
            },
            "emt": {"index": {}, "names": [], "ids": []},
            "urb": {"index": {}, "names": [], "ids": []},
        },
    }
    load_data()
    train_lines()
    transport_lines("metro")
    transport_lines("emt")
    transport_lines("urb")


def downloader_daily(queue):
    update_time = datetime.time(hour=5, tzinfo=pytz.timezone("Europe/Madrid"))
    queue.run_daily(
        update_data,
        update_time,
        days=(0,),
        context=queue,
        name="downloader_daily",
    )
