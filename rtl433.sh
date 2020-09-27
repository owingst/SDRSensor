#!/bin/bash 

###################################################################
#Script Name	:  sdrsensor.sh                                                                                            
#Description	:  Shell script to launch sdrsensor.py                                                                               
#Args           :                                                                                           
#Author       	:  Tim Owings                                                
#Email         	:  owingst@gmail.com                                           
###################################################################
rtl_433 -R23 -R40 -C customary -F json | mosquitto_pub -t Sensor -l -h 192.168.1.75
