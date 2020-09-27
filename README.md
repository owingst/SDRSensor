# SDRSensor

The SDRSensor project is one part of a two-part application. The other project is the Home project. The SDRSensor project represents the back-end while the Home project represents the front-end. The Home project is an IOS 14 based SwiftUI application, while the SDRSensor project is written using Python for a Raspberry Pi (model 3b).

The Home application was originally written for IOS 13 and used CocoaMQTT Pod. Since the CocoaMQTT library is written in Swift, it breaks whenever the Swift version changes. I decided to look for another MQTT library and decided on MQTT-Client-Framework which is written is Objective-C and is not impacted by Swift version changes.

Here are a couple of diagrams showing the architecture of these two apps.

![alt text](../media/SDRSensor-Page-1.jpg?raw=true)

![alt text](../media/SDRSensor-Page-2.jpg?raw=true)
