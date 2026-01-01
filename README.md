# Description
Source code of [@crtmadrid\_bot](https://t.me/crtmadrid_bot).

# Requirements
- python

# Run
- Install python dependencies.

    `pip install -r requirements.txt`

- Create a self-signed certificate in order to communicate with telegram server using SSL.

    `openssl req -newkey rsa:2048 -sha256 -nodes -keyout ferdinand.key
    -x509 -days 3650 -out ferdinand.pem`

- Create a copy of config.template.json and change the dummy values in .config.json.

    `cp config/config.json.template config/config.json`

    > - **token** - Telegram bot token, obtained from
    > [@BotFather](https://t.me/BotFather)
    >
    > - **webhook**: true to run the bot using webhooks. false to use polling.
    >
    > - **log_level**: set level of the logging module.
    > More info: [log levels](https://docs.python.org/3/library/logging.html#logging-levels)
    >
    > - **ip**: Your server ip, where the bot is hosted
    >
    > - **port**: Port to receive telegram updates: port must be 443, 80, 88 or 8443.
    >
    > - **cert**: Path to your server certificate (can be self-signed)

- Execute the bot.

    `python -m crtm`

    > **Note:** If you run the bot in port 80, it may be needed to run the bot as
    > superuser (**sudo**).

# License
    Copyright (c) 2022-2026 scmanjarrez. All rights reserved.
    This work is licensed under the terms of the MIT license.

For a copy, see
[LICENSE](LICENSE).
