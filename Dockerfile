FROM python:2

# set version label
LABEL maintainer="wjbeckett"

RUN mkdir /config

WORKDIR /config

RUN \
 echo "***** install python utils ****" && \
 apt-get update && \
 apt-get install -y \
    git && \
 pip install --no-cache-dir \
	paho-mqtt \
	pyyaml \
	pycrypto
RUN \
 echo "**** Grab latest version ****" && \
 git clone https://github.com/liaan/broadlink_ac_mqtt.git . && \
 cp -n sample_config.ym_ config.yml

COPY . .

CMD [ "python", "./monitor.py" ]

VOLUME /config