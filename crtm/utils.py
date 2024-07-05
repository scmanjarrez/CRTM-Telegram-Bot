#!/usr/bin/env python3
# SPDX-License-Identifier: MIT


# Copyright (c) 2022-2024 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

import json
import logging
import re
import traceback
import unicodedata
from datetime import datetime, time
from pathlib import Path

import crtm.database as db
import crtm.private.endpoints as end  # not uploaded for privacy reasons
import crtm.gui as gui
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
    "line": re.compile(r"(Línea) (.*):"),
    "orig": re.compile(r"(Origen:) (.*)"),
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


def download_api_data():
    emt_path = Path(FILES["emt"])
    emt_path.parent.mkdir(exist_ok=True)
    get = end.download_emt()
    if get.status_code != 200:
        return
    data = parse_api_data(get.json())
    with emt_path.open("w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    urb_path = Path(FILES["urb"])
    get = end.download_urb()
    if get.status_code != 200:
        return
    data = parse_api_data(get.json())
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
                names["station"][sts["i"]]["lineIds"] = data[
                    "uiStopIndexes"
                ][sts["i"]]
    return names


def parse_bici_data(data):
    names = {}
    for station in data["data"]:
        names[station["number"]] = {
            "id": station["id"],
            "name": station["name"],
        }
    return names


def load_data():
    # download_api_data()
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
    for idx, (station, info) in enumerate(
        DATA["raw"]["bici"].items()
    ):
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
        if name not in stations:
            stations[name] = {"idweb": set(), "cnt": 0}
        stations[name]["cnt"] += 1
        if "idMatriz" in st:
            if "idmatrix" not in stations[name]:
                stations[name]["idmatrix"] = set()
            stations[name]["idmatrix"].add(st["idMatriz"])
        stations[name]["idweb"].add(st["idweb"])
        if "idOcupacion" in st:
            if "idocup" not in stations[name]:
                stations[name]["idocup"] = []
            stations[name]["idocup"].append(st["idOcupacion"])
    staids = {}
    for k, v in stations.items():
        staid = list(v["idweb"])[0]
        if v["cnt"] > 1:
            if "idmatrix" in v:
                staid = list(v["idmatrix"])[0]
        else:
            if "idocup" in v:
                staid = v["idocup"][0]
        staids[k] = staid
    return staids


def metro_lines():
    staids = metro_ids()
    for idx, info in enumerate(
        DATA["raw"]["metro"]["red"]["estaciones"]["estacion"]
    ):
        staid = staids[info["name"]]
        DATA["proc"]["metro"]["index"][staid] = idx
        DATA["proc"]["metro"]["names"].append(info["name"])
        DATA["proc"]["metro"]["ids"].append(staid)
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


def send(
    update, msg, quote=True, reply_markup=None, disable_preview=True
):
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
    edit(update, "Es necesario iniciar el bot con /start antes de continuar.", None)


def weather_info(data):
    res = {
        "summ": data["summary"],
        "hum": f"{round(data['humidity'])}",
        "rain": ("0" if data["precipProbability"] is None
                 else round(data['precipProbability']*100)),
    }
    if "temperature" in data:
        res["temp"] = f"{data['temperature']:.1f}"
        if "unixTime" in data:
            res["hour"] = datetime.fromtimestamp(
                data["unixTime"]
            ).strftime("%H:%M")
    else:
        res["tempmin"] = f"{data['tempMin']:.1f}"
        res["tempmax"] = f"{data['tempMax']:.1f}"
        res["day"] = datetime.fromtimestamp(
            data["unixTime"]
        ).strftime("%d/%m")
    return res


def weather():
    get = req.get(
        f'{end.URL["weather"]}',
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
        "hours": [
            weather_info(hour)
            for hour in data["nextHoursData"]["list"]
        ],
        "days": [
            weather_info(day) for day in data["nextDaysData"]["list"]
        ],
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
        soup = BeautifulSoup(get.text, "html.parser")
        data = [
            [
                [el.text.strip() for el in row.select("td")]
                for row in plan.select(
                    "tr.recent-even, tr.recent-odd"
                )
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
                        info[DATA["idx"]["cerc"][idy]][tm[1]] = [
                            "",
                            [],
                        ]
                    info[DATA["idx"]["cerc"][idy]][tm[1]][0] = tm[3]
                    info[DATA["idx"]["cerc"][idy]][tm[1]][1].append(
                        (
                            tm[0] if tm[0] else "Llegando",
                            f"Vía {tm[4]}" if tm[4] else "",
                        )
                    )
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
                next1 = train.find("proximo")
                next2 = train.find("siguiente")
                times = []
                if next1 is not None and next1.text:
                    times.append(next1.text)
                if next2 is not None and next2.text:
                    times.append(next2.text)
                if not times:
                    times.append("No disponible")
                info[line.text][platform]["times"] = times
        return info


def real_time(transport, stop_id):
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
            sec = [
                str(binfo["s"] // 60)
                if binfo["s"] > 60
                else "Llegando"
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


def reformat_cercanias(text):
    text = text.replace("Llegadas", "<b>Llegadas</b>")
    text = text.replace("Salidas", "<b>Salidas</b>")
    text = RE["orig"].sub(r"\1 <code>\2</code>", text)
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
        f"- Probabilidad de lluvia: <code>{data['now']['rain']}%"
        f"</code>\n",
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
    msg = [f"Estadísticas de estación {stop}\n\n"]
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
                f"- <b>Bicis</b>: <code>{info['dock_bikes']}/{total}"
                f"</code>\n"
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
    msg = [f"Tiempos en estación {stop}\n\n"]
    data = metro(stop_id)
    if data is not None:
        if data:
            for line in data:
                msg.append(f"<b>Línea {line}:</b>\n")
                for platf, info in data[line].items():
                    msg.append(
                        f"- Destino: <code>{info['direction']}</code>\n"
                    )
                    msg.append(f"- Andén: <code>{platf}</code>\n")
                    msg.append(
                        f"- Tiempo(s): "
                        f"<code>{', '.join(info['times'])}"
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
                        "{}{}".format(
                            tm[0], f" ({tm[1]})" if tm[1] else ""
                        )
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
    msg = [
        f"Tiempos en parada {stop} ({stop_id.replace(PREFIX[transport], '')})\n\n"
    ]
    data = real_time(transport, stop_id)
    if data is not None:
        if data:
            for line in data:
                msg.append(f"<b>Línea {line}:</b>\n")
                msg.append(
                    f"- Destino: <code>{data[line]['name']}</code>\n"
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
    if transport == "bici":
        return DATA["proc"][transport]["stopids"].index(int(stop_id))
    return DATA["proc"][transport]["index"][stop_id]


def store_suggestion(text):
    with open("suggestions.txt", "a") as f:
        f.write(f"{text}\n\n")


def normalize(word):
    nfkd = unicodedata.normalize("NFKD", word)
    return "".join(
        [c for c in nfkd if not unicodedata.combining(c)]
    ).upper()


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
            stop_data(transport, index, inline)
            for _, index in uniq.items()
        ]
    else:
        return [
            stop_data(transport, index, inline) for index, _ in stops
        ]


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
    return InlineQueryResultArticle(
        id=rid,
        title=msg.capitalize(),
        input_message_content=InputTextMessageContent(
            f"Recopilando {msg}"
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
