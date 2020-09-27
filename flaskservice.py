#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Title           : flaskservice.py
# Description     : This script is a Flask Service
# Created By      : Tim Owings
# Created Date    : Mon January 26 2020
# Usage           : /home/pi/sdr/flaskservice.sh
# Python          : 3.7.3
# =============================================================================
# Imports
import json
import time
import sqlite3
import os
import configparser
from flask import Flask
import RPi.GPIO as GPIO
# =============================================================================

app = Flask(__name__)

RELAY_CH1 = 18
CONNECTED = False
DATABASE = None
BROKER_ADDRESS = None


def logStatus(msg):
    """ Function to write logs to a file. Never could get Flask logging to a file to work.... """
    try:
        fhandle = open('/home/pi/sdr/flaskservice.log', 'a')
        fhandle.write(msg)
        fhandle.close()
    except Exception:
        logStatus("logStatus: exception\n")


def getConfigValues():
    """ getConfigValues """

    global BROKER_ADDRESS
    global DATABASE

    try:
        config = configparser.ConfigParser()
        config.read('/home/pi/sdr/sdrsensor.ini')
        DATABASE = config['Sensor']['database_path']
        BROKER_ADDRESS = config['Sensor']['broker_address']
        return

    except Exception:
        logStatus("getConfigValues: exception\n")


def getConnection():
    """ Get SQLite DB Connection """

    global DATABASE

    for _ in range(0, 10):

        try:
            conn = sqlite3.connect(DATABASE)
            return conn

        except Exception as e:

            logStatus("getConnection: Exception type = \n" + e.__class__)
            time.sleep(2)
            continue

        else:
            logStatus("getConnection: no exception this pass so break out\n")
            break


@app.route('/getProcs/<name>', methods=['GET'])
def getProcs(name):
    """ API to get process ids """

    cmd = "ps -ef | grep -v grep | grep -Hsi " + name

    try:

        proclist = os.popen(cmd).read()

        return proclist

    except Exception:
        logStatus("getProcs: exception\n")


@app.route('/shutdown', methods=['GET'])
def shutdown():
    """ API to shutdown Pi """

    os.system("sudo poweroff")


@app.route('/opendoor', methods=['GET'])
def openDoor():
    """ API to open/close Garage Door """

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_CH1, GPIO.OUT)
        GPIO.output(RELAY_CH1, GPIO.LOW)
        time.sleep(1)
        GPIO.cleanup()
        logStatus("Open Door Request Processed Successfully\n")
        return "Open Door Request Processed Successfully"

    except Exception:
        logStatus("opendoor:openDoor: exception\n")


@app.route('/getTemp', methods=['GET'])
def getTemp():
    """ API to get latest temperature/humidity from DB """

    conn = None
    cur = None
    sql = "SELECT datetime(MAX(ts), 'localtime'), temperature, humidity, batterylow FROM weather"

    try:

        conn = getConnection()
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        if row:
            eventTime = row[0]
            temp = row[1]
            humidity = row[2]
            batterylow = row[3]
            jsonObj = json.dumps(
                {'Result': 0, 'msgType': 'temp', 'temperature': temp, 'humidity': humidity, 'eventTime': eventTime, 'batterylow': batterylow})
            logStatus("getTemp Request Processed Successfully\n")
        else:
            logStatus('getTemp: no data returned\n')
            jsonObj = json.dumps({'Result': 1})

        return jsonObj

    except Exception:

        logStatus("getTemp: exception\n")
        return "getTemp Exception"

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getDoorStatus', methods=['GET'])
def getDoorStatus():
    """ API to get latest DoorStatus from DB """

    conn = None
    cur = None
    # sql = "SELECT status, esn, MAX(eventTime) FROM doorstatus"
    sql = "select datetime(MAX(ts), 'localtime'), esn, status, batterylow from doorstatus"

    try:
        conn = getConnection()
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        if row:
            eventTime = row[0]
            esn = row[1]
            status = row[2]
            batterylow = row[3]
            jsonObj = json.dumps(
                {'Result': 0, 'msgType': 'door', 'eventTime': eventTime, 'esn': esn, 'status': status, 'batterylow': batterylow})
            logStatus("getDoorStatus Request Processed Successfully\n")
        else:
            logStatus("getDoorStatus: no data returned\n")
            jsonObj = json.dumps({'Result': 1})

        return jsonObj

    except Exception:
        logStatus("getDoorStatus: Exception\n")
        return "getDoorStatus: Exception"

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()

# Init stuff


f = None

try:

    logStatus("Flask Service Started\n")
    getConfigValues()

except Exception as e:
    logStatus("init: exception\n")

finally:
    if f is not None:
        f.close()

if __name__ == '__main__':

    app.run(host='192.168.1.75', port=5000, threaded=True, debug=True)
