#!/usr/bin/env python3
# SPDX-License-Identifier: MIT


# Copyright (c) 2022-2026 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

import json
import logging
import re
import traceback
import unicodedata
from datetime import datetime, time
from pathlib import Path

import pytz  # type: ignore
import requests as req  # type: ignore
from bs4 import BeautifulSoup
from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    ParseMode,
)
from telegram.error import BadRequest, Unauthorized

import crtm.database as db
import crtm.gui as gui
import crtm.private.endpoints as end  # not uploaded for privacy reasons

STATE = {}
KB_WIDTH = 4
LOGO = (
    "https://raw.githubusercontent.com/"
    "scmanjarrez/CRTM-Telegram-Bot/master/logos"
)
RE = {
    "line": re.compile(r"(Línea) (.*):"),
    "dest": re.compile(r"(Destino:) (.*)"),
    "time": re.compile(r"(Tiempo\(s\):) (.*)"),
}
CMD_TRANS = {
    "bici": ("bici", "estación"),
    "metro": ("metro", "estación"),
    "cercanias": ("cerc", "estación"),
    "emt": ("emt", "parada"),
    "interurbano": ("urb", "parada"),
    "type_bus": ("emt", "urb"),
}
FILES = {
    "db": "config/crtm.db",
    "cfg": "config/config.json",
    "token": "config/token",
    "bici_token": "config/bici_token",
    "bici": "data/bicimad.json",
    "metro": "data/metro.json",
    "cerc": "data/cercanias.json",
    "emt": "data/emt.json",
    "urb": "data/interurbanos.json",
}
OCCUP = {
    0: "Baja",
    1: "Media",
    2: "Alta",
    3: "No disponible",
}
PREFIX = {
    "emt": "EMT_",
    "urb": "CRTM_par_8_",
}
CONFIG = {}
DATA = {}


# def _debug_request(req):
#     print(req.request.url, req.request.body, req.request.headers)


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


def admin(key):
    return CONFIG["admin"][key]


def download_api_data():
    # --- cercanias
    cerc_path = Path(FILES["cerc"])
    cerc_path.parent.mkdir(exist_ok=True)
    get = end.download_cerc()
    if get.status_code != 200:
        return
    data = parse_cerc_data(get.json())
    with cerc_path.open("w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    # --- emt
    emt_path = Path(FILES["emt"])
    emt_path.parent.mkdir(exist_ok=True)
    get = end.download_emt()
    if get.status_code != 200:
        return
    data = parse_api_data(get.json())
    with emt_path.open("w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    # --- interurbanos
    urb_path = Path(FILES["urb"])
    get = end.download_urb()
    if get.status_code != 200:
        return
    data = parse_api_data(get.json())
    # --- bicimad
    with urb_path.open("w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    bici_path = Path(FILES["bici"])
    get = end.download_bici()
    if get.status_code != 200:
        return
    data = parse_bici_data(get.json())
    with bici_path.open("w") as f:
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


def parse_bici_data(data):
    names = {}
    for station in data["data"]:
        names[station["number"]] = {
            "id": station["id"],
            "name": station["name"],
        }
    return names


def parse_cerc_data(data):
    names = []
    for station in data:
        stop = {
            "id": station["s"]["h"],
            "name": station["s"]["n"],
            "lineIds": list(set([s["n"][:2] for s in station["r"]])),
        }
        names.append(stop)
    return names


def load_data():
    ## TODO: uncomment this line!!!!
    download_api_data()
    with open(FILES["bici"], "r") as f:
        DATA["raw"]["bici"] = json.load(f)
    with open(FILES["cerc"], "r") as f:
        DATA["raw"]["cerc"] = json.load(f)
    with open(FILES["metro"], "r") as f:
        DATA["raw"]["metro"] = json.load(f)
    with open(FILES["emt"], "r") as f:
        DATA["raw"]["emt"] = json.load(f)
    with open(FILES["urb"], "r") as f:
        DATA["raw"]["urb"] = json.load(f)


def bici_lines():
    for idx, (station, info) in enumerate(DATA["raw"]["bici"].items()):
        DATA["proc"]["bici"]["index"][station] = idx
        DATA["proc"]["bici"]["names"].append(info["name"])
        DATA["proc"]["bici"]["ids"].append(station)
        DATA["proc"]["bici"]["stopids"].append(info["id"])


def train_lines():
    for idx, info in enumerate(DATA["raw"]["cerc"]):
        DATA["proc"]["cerc"]["index"][info["id"]] = idx
        DATA["proc"]["cerc"]["names"].append(info["name"])
        DATA["proc"]["cerc"]["ids"].append(info["id"])
        first = info["name"][0]
        if first not in DATA["proc"]["cerc"]["stops"]:
            DATA["proc"]["cerc"]["stops"][first] = []
        DATA["proc"]["cerc"]["stops"][first].append(idx)
        for line in info["lineIds"]:
            if line not in DATA["proc"]["cerc"]["lines"]:
                DATA["proc"]["cerc"]["lines"][line] = {}
            if first not in DATA["proc"]["cerc"]["lines"][line]:
                DATA["proc"]["cerc"]["lines"][line][first] = []
            DATA["proc"]["cerc"]["lines"][line][first].append(idx)


def metro_ids():
    stations = {}
    for st in DATA["raw"]["metro"]["red"]["estaciones"]["estacion"]:
        name = st["name"]
        web = st["idweb"]
        if name not in stations:
            stations[name] = {"idweb": set(), "idmatriz": set()}
        if "idMatriz" in st:
            stations[name]["idmatriz"].add(st["idMatriz"])
        stations[name]["idweb"].add(web)
    staids = {}
    staall = {}
    for k, v in stations.items():
        staid = list(v["idweb"])[0]
        if len(v["idmatriz"]) > 0:
            staall[staid] = list(v["idmatriz"])[0]
        staids[k] = staid
    return staids, staall


def metro_lines():
    staids, staall = metro_ids()
    DATA["proc"]["metro"]["idsmat"] = staall
    for idx, info in enumerate(
        DATA["raw"]["metro"]["red"]["estaciones"]["estacion"]
    ):
        staid = staids[info["name"]]
        DATA["proc"]["metro"]["index"][staid] = idx
        DATA["proc"]["metro"]["names"].append(info["name"])
        DATA["proc"]["metro"]["ids"].append(staids[info["name"]])
        first = info["name"][0]
        if first not in DATA["proc"]["metro"]["stops"]:
            DATA["proc"]["metro"]["stops"][first] = []
        DATA["proc"]["metro"]["stops"][first].append(idx)
        line_id = info["linea"]
        if line_id not in DATA["proc"]["metro"]["lines"]:
            DATA["proc"]["metro"]["lines"][line_id] = {}
        if first not in DATA["proc"]["metro"]["lines"][line_id]:
            DATA["proc"]["metro"]["lines"][line_id][first] = []
        DATA["proc"]["metro"]["lines"][line_id][first].append(idx)


def transport_lines(transport):
    for idx, (station, info) in enumerate(
        DATA["raw"][transport]["station"].items()
    ):
        DATA["proc"][transport]["index"][station] = idx
        DATA["proc"][transport]["names"].append(info["name"])
        DATA["proc"][transport]["ids"].append(station)


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


def not_started(update):
    send(update, "Es necesario iniciar el bot con /start antes de continuar.")


def not_started_gui(update):
    edit(
        update,
        "Es necesario iniciar el bot con /start antes de continuar.",
        None,
    )


def weather_info(data):
    res = {
        "summ": data["summary"],
        "hum": f"{round(data['humidity'])}",
        "rain": (
            "0"
            if data["precipProbability"] is None
            else round(data["precipProbability"] * 100)
        ),
    }
    if "temperature" in data:
        res["temp"] = f"{data['temperature']:.1f}"
        if "unixTime" in data:
            res["hour"] = datetime.fromtimestamp(data["unixTime"]).strftime(
                "%H:%M"
            )
    else:
        res["tempmin"] = f"{data['tempMin']:.1f}"
        res["tempmax"] = f"{data['tempMax']:.1f}"
        res["day"] = datetime.fromtimestamp(data["unixTime"]).strftime("%d/%m")
    return res


def weather():
    get = req.get(
        f"{end.URL['weather']}",
        params={
            "lat": 40.49,
            "lng": -3.68,
            "appId": "mad",
            "lang": "es",
        },
        headers=end.headers(),
    )
    data = get.json()
    info = {
        "now": weather_info(data["nowData"]),
        "hours": [weather_info(hour) for hour in data["nextHoursData"]["list"]],
        "days": [weather_info(day) for day in data["nextDaysData"]["list"]],
    }
    return info


def bici(stop_id):
    try:
        get = end.get_bici(stop_id)
    except req.exceptions.ReadTimeout:
        return None
    else:
        return get.json()


def cercanias(stop_id):
    try:
        get = end.get_cercanias(stop_id)
    except req.exceptions.ReadTimeout:
        return None
    else:
        if get.text in (
            "Rate exceeded.",
            "Error: could not handle the request\n",
        ):
            return None
        data = get.json()
        if "code" in data:
            return None
        info = {}
        for train in data["stopRoutesSimpleRealTimesList"]:
            if train["hi"] not in info:
                info[train["hi"]] = {}
            if train["h"] not in info[train["hi"]]:
                info[train["hi"]][train["h"]] = []
            info[train["hi"]][train["h"]].append((train["p"], train["s"]))
        return info


def metro(stop_id):
    try:
        get = end.get_metro(stop_id)
    except req.exceptions.ReadTimeout:
        return None
    else:
        soup = BeautifulSoup(get.text, "lxml-xml")
        data = soup.find_all("Vtelindicadores")
        info = {}
        for train in data:
            line = train.find("linea")
            if line is not None:
                if line.text not in info:
                    info[line.text] = {}
                platform = train.find("anden").text
                info[line.text][platform] = {
                    "direction": train.find("sentido").text
                }
                prev = datetime.fromisoformat(
                    train.find("fechaHoraEmisionPrevision").text
                )
                now = datetime.now(prev.tzinfo)
                minutes_passed = (now - prev).seconds // 60
                next1 = train.find("proximo")
                next2 = train.find("siguiente")
                times = []
                if next1 is not None and next1.text:
                    if next1.text == "0":
                        if minutes_passed < 1:
                            times.append("Llegando")
                        else:
                            times.append("A la espera de previsión")
                    else:
                        times.append(f"{next1.text}min")
                if next2 is not None and next2.text:
                    if next2.text == "0":
                        if minutes_passed < 1:
                            times.append("Llegando")
                        else:
                            times.append("A la espera de previsión")
                    else:
                        times.append(f"{next2.text}min")
                if not times:
                    times.append("No disponible")
                info[line.text][platform]["times"] = times
        return info


def bus(transport, stop_id):
    try:
        get = end.get_bus(transport, stop_id)
    except req.exceptions.ReadTimeout:
        return None
    else:
        if get.text in (
            "Rate exceeded.",
            "Error: could not handle the request\n",
        ):
            return None
        data = get.json()
        if "code" in data:
            return None
        info = {}
        for bs in data["rtl"]:
            times = []
            for binfo in bs["l"]:
                time = "Llegando"
                if binfo["s"] > 60:
                    if binfo["s"] > 3600:
                        time = (
                            f"{binfo['s'] // 3600}:"
                            f"{(binfo['s'] % 3600) // 60:02}h"
                        )
                    else:
                        time = f"{binfo['s'] // 60}min"
                times.append(time)
            bid = DATA["raw"][transport]["line"][bs["r"]]["id"]
            info[bid] = {}
            info[bid]["name"] = bs["h"]
            info[bid]["times"] = times
        return info


def transport_info(transport, index):
    ids = "ids"
    if transport == "bici":
        ids = "stopids"
    return (
        DATA["proc"][transport]["names"][int(index)],
        DATA["proc"][transport][ids][int(index)],
    )


def chunk(lst):
    for idx in range(0, len(lst), KB_WIDTH):
        yield lst[idx : idx + KB_WIDTH]


def sort_lines(line):
    if line.isdigit():
        return False, int(line)
    return True, line


def sort_cerc_lines(line):
    return int(line[1:])


def reformat(text):
    text = RE["line"].sub(r"<b>\1 \2</b>:", text)
    text = RE["dest"].sub(r"\1 <code>\2</code>", text)
    text = RE["time"].sub(r"\1 <code>\2</code>", text)
    return text


def text_weather():
    data = weather()
    msg = [
        f"<b>Clima en este momento</b>\n"
        f"- Resumen: <code>{data['now']['summ']}</code>\n",
        f"- Temperatura: <code>{data['now']['temp']}ºC</code>\n",
        f"- Humedad: <code>{data['now']['hum']}%</code>\n",
        f"- Probabilidad de lluvia: <code>{data['now']['rain']}%</code>\n",
    ]
    msg.append("\n<b>Clima en las próximas horas</b>\n")
    for hour in data["hours"][0:9]:
        msg.append(
            f"- {hour['hour']}, <code>{hour['summ']} "
            f"({hour['temp']}ºC, {hour['hum']}%, "
            f"{hour['rain']}%)</code>\n"
        )
    msg.append("\n<b>Clima en los próximos días</b>\n")
    for day in data["days"][0:9]:
        msg.append(
            f"- {day['day']}, <code>{day['summ']} "
            f"({day['tempmin']}-{day['tempmax']}ºC, "
            f"{day['hum']}%, {day['rain']}%)</code>\n"
        )
    return msg


def text_bici(stop, stop_id):
    msg = [f"Estadísticas de estación <b>{stop}</b>\n\n"]
    data = bici(stop_id)
    if data is not None:
        if data and data["data"]:
            info = data["data"][0]
            state = "activa" if info["activate"] else "inactiva"
            msg.append(f"- <b>Estado</b>: <code>{state}</code>\n")
            addr = info["address"]
            if addr[-1] == ",":
                addr = addr[:-1]
            msg.append(f"- <b>Dirección</b>: <code>{addr}</code>\n")
            msg.append(
                f"- <b>Nivel ocupación</b>: <code>{OCCUP[info['light']]}"
                f"</code>\n"
            )
            total = info["total_bases"]
            msg.append(
                f"- <b>Bicis</b>: <code>{info['dock_bikes']}/{total}</code>\n"
            )
            msg.append(
                f"- <b>Anclajes</b>: <code>{info['free_bases']}/{total}"
                f"</code>\n"
            )
            msg.append(
                f"- <b>Anclajes reservados</b>: "
                f"<code>{info['reservations_count']}/{total}</code>\n"
            )
        else:
            msg.append("<b>No hay información disponible.</b>")
    else:
        msg.append(
            "<b>Debido a un error en el servicio de BiciMAD "
            "no es posible obtener información en estos momentos.</b>"
        )
    return msg


def text_metro(stop, stop_id):
    msg = [f"Tiempos en estación <b>{stop}</b>\n\n"]
    data = metro(stop_id)
    if data is not None:
        if data:
            for line in sorted(data, key=sort_line):
                msg.append(f"<b>Línea {line}:</b>\n")
                for platf, info in data[line].items():
                    msg.append(
                        f"- Destino: <code>{info['direction']} "
                        f"(Andén {platf})</code>\n"
                    )
                    msg.append(
                        f"- Tiempo(s): "
                        f"<code>{', '.join(info['times'])}</code>"
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
    msg = [f"Tiempos en estación <b>{stop}</b>\n\n"]
    data = cercanias(stop_id)
    if data is not None:
        if data:
            for line in sorted(data, key=sort_line):
                msg.append(f"<b>Línea {line}:</b>\n")
                for direction, info in data[line].items():
                    msg.append(
                        f"- Destino: <code>{direction} "
                        f"(Vía {info[0][0]})</code>\n"
                    )
                    times = []
                    for train in info:
                        time = "Llegando"
                        if train[1] > 60:
                            if train[1] > 3600:
                                time = (
                                    f"{train[1] // 3600}:"
                                    f"{(train[1] % 3600) // 60:02}h"
                                )
                            else:
                                time = f"{train[1] // 60}min"
                        times.append(time)
                    msg.append(
                        f"- Tiempo(s): <code>{', '.join(times)}</code>\n\n"
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
    msg = [
        f"Tiempos en parada <b>{stop} "
        f"({stop_id.replace(PREFIX[transport], '')})</b>\n\n"
    ]
    data = bus(transport, stop_id)
    if data is not None:
        if data:
            for line in sorted(data, key=sort_line):
                msg.append(f"<b>Línea {line}:</b>\n")
                msg.append(f"- Destino: <code>{data[line]['name']}</code>\n")
                msg.append(
                    f"- Tiempo(s): "
                    f"<code>{', '.join(data[line]['times'])}</code>"
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
    if transport == "bici":
        return DATA["proc"][transport]["stopids"].index(int(stop_id))
    return DATA["proc"][transport]["index"][stop_id]


def store_message(text, rep=False):
    file = "suggestions.txt"
    if rep:
        file = "reports.txt"
    with open(file, "a") as f:
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


def stop_data(transport, index, inline=False):
    stop, stop_id = transport_info(transport, index)
    prefix = "time_cli"
    if inline:
        prefix = "time_inline"
    if transport in PREFIX.keys():
        stop = f"{stop} ({stop_id.replace(PREFIX[transport], '')})"
    return (stop, f"{prefix}_{transport}_{index}")


def stopname_matches(transport, stopnames, inline=False):
    stops = list(enumerate(DATA["proc"][transport]["names"]))
    for word in stopnames:
        stops = [
            (index, stop)
            for index, stop in stops
            if normalize(word) in normalize(stop)
        ]
    if transport == "metro":
        uniq = {stop: idx for idx, stop in stops}
        return [
            stop_data(transport, index, inline) for _, index in uniq.items()
        ]
    else:
        return [stop_data(transport, index, inline) for index, _ in stops]


def stopnumber_match(transport, stopnumber):
    match = False
    for idx, stop_id in enumerate(DATA["proc"][transport]["ids"]):
        if transport == "bici":
            cmp = stopnumber
        else:
            cmp = f"{PREFIX[transport]}{stopnumber}"
        if cmp == stop_id:
            match = True
            break
    return match, idx


def text_transport(transport, index):
    stop, stop_id = transport_info(transport, index)
    if transport == "bici":
        msg = text_bici(stop, stop_id)
    elif transport == "metro":
        msg = text_metro(stop, stop_id)
    elif transport == "cerc":
        msg = text_cercanias(stop, stop_id)
    else:
        msg = text_bus(transport, stop, stop_id)
    return msg, stop_id


def result(transport, rid, msg):
    _msg = msg.split()
    pref = _msg[:3]
    sta = _msg[3:]
    return InlineQueryResultArticle(
        id=rid,
        title=msg.capitalize(),
        input_message_content=InputTextMessageContent(
            f"Recopilando {' '.join(pref)} <b>{' '.join(sta)}</b>",
            parse_mode=ParseMode.HTML,
        ),
        reply_markup=gui.markup([("🔃 Actualizar 🔃", rid)]),
        thumb_url=f"{LOGO}/{transport}.png",
        thumb_height=48,
        thumb_width=48,
    )


def is_bus(transport):
    return transport in CMD_TRANS["type_bus"]


def update_data(_):
    global DATA
    DATA = {
        "cfg": None,
        "token": None,
        "bici_token": None,
        "raw": {
            "bici": None,
            "metro": None,
            "cerc": None,
            "emt": None,
            "urb": None,
        },
        "idx": {
            "cerc": {0: "salidas", 1: "llegadas"},
        },
        "proc": {
            "bici": {
                "index": {},
                "names": [],
                "ids": [],
                "stopids": [],
            },
            "metro": {
                "lines": {},
                "stops": {},
                "index": {},
                "names": [],
                "ids": [],
                "idsmat": {},
            },
            "cerc": {
                "lines": {},
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
    bici_lines()
    train_lines()
    metro_lines()
    transport_lines("emt")
    transport_lines("urb")


def downloader_daily(queue):
    update_time = time(hour=5, tzinfo=pytz.timezone("Europe/Madrid"))
    queue.run_daily(
        update_data,
        update_time,
        days=(0,),
        context=queue,
        name="downloader_daily",
    )


def sort_line(s):
    numeric = "".join(filter(str.isdigit, s))
    alpha = "".join(filter(str.isalpha, s))
    num = int(numeric) if numeric else 0
    return (num, alpha)
