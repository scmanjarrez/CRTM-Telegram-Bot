# Descripción
Código fuente del bot accesible desde [@crtmadrid\_bot](https://t.me/crtmadrid_bot).

# Requisitos
- python

# Ejecución
- Instala las dependencias de python.

    `pip install -r requirements.txt`

- Crea un certificado autofirmado para que el bot pueda comunicarse con los servidores
  de telegram mediante SSL.

    `openssl req -newkey rsa:2048 -sha256 -nodes -keyout ferdinand.key
    -x509 -days 3650 -out ferdinand.pem`

- Crea una copia del fichero config.template.json y modifica los valores del archivo .config.json.

    `cp config.template.json .config.json`

    > - **token**: Token del bot de telegram, obtenido a través de [@BotFather](https://t.me/BotFather)
    >
    > - **ip**: La IP del servidor donde se alejará el bot
    >
    > - **port**: El puerto donde se recibirán las actualizaciones de telegram: sólo es posible usar los puertos 443, 80, 88 o 8443.
    >
    > - **cert**: El path al certificado (puede ser autofirmado)

- Ejecuta el bot.

    `./crtm.py`

    > **Nota:** Para ejecutar el bot en el puerto 80, es posible que debas ejecutarlo
    > con permisos de superusuario (**sudo**).


# Licencia
    Copyright (c) 2022 scmanjarrez. All rights reserved.
    This work is licensed under the terms of the MIT license.

Puedes encontrar la licencia completa en
[LICENSE](LICENSE).
