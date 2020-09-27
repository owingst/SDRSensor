#!/bin/bash 

###################################################################
#Script Name	:  flaskservice.sh                                                                                            
#Description	:  Shell script to launch Flask Service                                                                             
#Args           :                                                                                           
#Author       	:  Tim Owings                                                
#Email         	:  owingst@gmail.com                                           
###################################################################
set FLASK_DEBUG=true
FLASK_APP=/home/pi/sdr/flaskservice.py flask run --host=192.168.1.75 --port=5000

