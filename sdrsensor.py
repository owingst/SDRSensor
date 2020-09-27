#!/usr/bin/env python3
""" SDRSensor Module """
# -*- coding: utf-8 -*-
# =============================================================================
# Title           : sdrsensor.py
# Description     : This script handles Garage Door movements
# Created By      : Tim Owings
# Created Date    : Thur January 23 2020
# Usage           : /home/pi/launcher.sh
# Python          : 3.7.3
# =============================================================================
# Imports
import sys
import time
import logging
import json
import sqlite3
from datetime import datetime
import configparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import paho.mqtt.client as mqtt
# =============================================================================

CONNECTED = False
CLIENTID = None
MQTTCLIENT = None
MQTT_TOPIC = None
LASTTEMP = None
LASTHUM = None
DATABASE_NAME = None
BROKER_ADDRESS = None
EMAIL = None
APP_PASSWORD = None
SMS_GATEWAY = None
ALT_GATEWAY = None
SMTP_SERVER = None
SMTP_PORT = None
LASTDOOR = None


def getConfigValues():
    """ getConfigValues """
    global BROKER_ADDRESS
    global EMAIL
    global APP_PASSWORD
    global SMS_GATEWAY
    global ALT_GATEWAY
    global SMTP_SERVER
    global SMTP_PORT
    global CLIENTID
    global MQTT_TOPIC
    global DATABASE_NAME

    try:
        config = configparser.ConfigParser()
        config.read('/home/pi/sdr/sdrsensor.ini')
        BROKER_ADDRESS = config['Sensor']['broker_address']
        EMAIL = config['Sensor']['email']
        APP_PASSWORD = config['Sensor']['app_password']
        SMS_GATEWAY = config['Sensor']['sms_gateway']
        ALT_GATEWAY = config['Sensor']['alt_gateway']
        SMTP_SERVER = config['Sensor']['smtp_server']
        SMTP_PORT = config['Sensor']['smtp_port']
        CLIENTID = config['Sensor']['client_id']
        MQTT_TOPIC = config['Sensor']['mqtt_topic']
        DATABASE_NAME = config['Sensor']['database_name']
        return

    except Exception as e:
        logging.exception("getConfigValues: exception in getConfigValues is {}\n".format(e))


def smssend(textAddr):
    """ Send SMS Message via Gmail SMS """

    server = None
    global EMAIL
    global SMTP_SERVER
    global SMTP_PORT
    global APP_PASSWORD

    try:

        logging.debug("smssend: Text to {}\n".format(textAddr))

        datestr = datetime.now()
        msgstr = "Garage door opened " + datestr.strftime("%m/%d/%Y, %H:%M:%S") + '\n'
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)

        server.starttls()

        server.login(EMAIL, APP_PASSWORD)

        msg = MIMEMultipart()

        msg['From'] = EMAIL
        msg['To'] = textAddr

        msg['Subject'] = 'Garage Door Opened Notification\n'

        body = msgstr

        msg.attach(MIMEText(body, 'plain'))

        sms = msg.as_string()

        server.sendmail(EMAIL, textAddr, sms)

    except Exception as e:
        logging.exception("smssend: Exception is {}\n".format(e))

    finally:
        if server is not None:
            server.quit()


def getConnection():
    """ Get SQLite DB Connection """

    global DATABASE_NAME

    for _ in range(0, 10):

        try:
            conn = sqlite3.connect(DATABASE_NAME)
            return conn

        except Exception as e:

            logging.exception("getConnection: Exception is {}\n".format(e))
            time.sleep(2)
            continue

        else:
            logging.debug("getConnection: no exception this pass so break out\n")
            break


def insertTemp(temperature, humidity, batterylow):
    """ Insert Temp """

    conn = None

    try:

        conn = getConnection()

        conn.execute("INSERT INTO weather (temperature, humidity, batterylow) values(?,?,?)", (temperature, humidity, batterylow))

        conn.commit()

        return 0

    except Exception as e:
        logging.exception("insertTemp: Exception is {}\n".format(e))
        return -1

    finally:
        if conn is not None:
            conn.close()


def insertDoorStatus(esn, status, batterylow):
    """ Insert DoorStatus """

    conn = None

    try:

        conn = getConnection()

        conn.execute("INSERT INTO doorstatus(esn, status, batterylow) values(?,?,?)", (esn, status, batterylow))

        conn.commit()

        return 0

    except Exception as e:
        logging.exception("insertDoorStatus: Exception is {}\n".format(e))
        return -1

    finally:
        if conn is not None:
            conn.close()


def sig_handler(signum):
    """ sig_handler """

    logging.debug("sig_handler: received signal is {}\n".format(signum))
    sys.exit()


def mqttsetup():
    """ Setup MQTT """

    global BROKER_ADDRESS
    global CLIENTID
    global MQTTCLIENT

    try:

        MQTTCLIENT = mqtt.Client(CLIENTID, clean_session=True)
        MQTTCLIENT.on_connect = on_connect
        MQTTCLIENT.on_message = on_message
        MQTTCLIENT.on_disconnect = on_disconnect
        MQTTCLIENT.connect(BROKER_ADDRESS, 1883, 60)

    except Exception as e:
        logging.exception("mqttsetup: mqttsetup connect exception is {}\n".format(e))


def on_disconnect(_client, _userdata, rc):
    """ on_disconnect """

    logging.debug("on_disconnect: rc is {}\n".format(rc))

    global CONNECTED

    if rc != 0:

        logging.error("Unexpected disconnection, so try and reconnect\n")

    try:
        CONNECTED = False
        mqttsetup()

    except Exception as e:
        logging.exception("on_disconnect: Exception in on_disconnect is {}\n".format(e))


def on_connect(client, _userdata, _flags, rc):
    """ on_connect """

    global CONNECTED

    if rc == 0:
        logging.debug("on_connect: Connected with result code {}\n".format(str(rc)))
        CONNECTED = True
        client.subscribe("Sensor")
    else:
        logging.error("on_connect: Bad connection with result code {}\n".format(str(rc)))
        CONNECTED = False
        mqttsetup()


def on_message(_client, _userdata, msg):
    """ on_message """

    try:

        data = json.loads(msg.payload.decode())

        eventid = data['id']

        batterylow = data['battery_low']

        model = data['model']

        if (model.startswith("Acurite") and (eventid == 11209)):

            temperature = round(data['temperature_F'])

            humidity = data['humidity']

            logging.debug("on_message: temperature %d   humidity %d  batteryLow %d\n", temperature, humidity, batterylow)

            processTempDB(temperature, humidity, batterylow)

        elif model.startswith("DSC"):

            esn = data['esn']
            status = data['closed']

            if esn == "246fc4":

                processDoorStatusDB(esn, status, batterylow)

        else:
            logging.error("on_message: Unknown device: model: {} eventId: {}\n".format(model, eventid))

    except Exception as e:

        logging.exception("on_message: Exception : {}".format(str(e.__str__).split(" ")[3]))
        return


def processTempDB(temperature, humidity, batterylow):
    """ processTempDB """

    global LASTTEMP
    global LASTHUM
    global MQTTCLIENT

    try:
        if (temperature != LASTTEMP) or (humidity != LASTHUM):

            rc = insertTemp(temperature, humidity, batterylow)
            if rc < 0:
                logging.error("processTempDB: Error inserting row in weather table\n")
            else:
                jsonObj = json.dumps({'type': 'temp', 'temperature': temperature, 'humidity': humidity, 'doorstatus': None, 'battery': batterylow})
                logging.debug("processTempDB: Publishing json obj of {}\n".format(jsonObj))
                MQTTCLIENT.publish("Changed", jsonObj, qos=0, retain=False)

            LASTTEMP = temperature
            LASTHUM = humidity

    except Exception as e:
            logging.exception("processTempDB: Exception is {}\n".format(e))


def processDoorStatusDB(esn, status, batterylow):
    """ processDoorStatusDB """

    global LASTDOOR
    global MQTTCLIENT
    global SMS_GATEWAY
    global ALT_GATEWAY

    try:

        rc = insertDoorStatus(esn, status, batterylow)

        if rc < 0:

            logging.error("processDoorStatusDB: Error inserting row in doorstatus table\n")

        else:

            if ((status == 0) and (LASTDOOR != status)):
                logging.debug("processDoorStatusDB: status is {} so send an sms\n".format(status))
                smssend(SMS_GATEWAY)
                smssend(ALT_GATEWAY)

        LASTDOOR = status

        jsonObj = json.dumps({'type': 'door', 'temperature': None, 'humidity': None, 'doorstatus': status, 'battery': batterylow})
        logging.debug("processDoorStatusDB: Publishing json obj of {}\n".format(jsonObj))
        MQTTCLIENT.publish("Changed", jsonObj, qos=0, retain=False)

    except Exception as e:
        logging.exception("processDoorStatusDB: Exception is {}\n".format(e))


def main():
    """ Main function """

    global MQTTCLIENT

    try:

        getConfigValues()
        time.sleep(5)
        mqttsetup()

        MQTTCLIENT.loop_forever()

    except Exception as e:
        logging.exception("Exception in main{}\n".format(e))


logging.basicConfig(filename='/home/pi/sdr/sdrsensor.log', level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s")

if __name__ == "__main__":
    main()
