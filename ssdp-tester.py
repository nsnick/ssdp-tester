#!/usr/bin/python

import socket
import urllib2
from urlparse import urlparse
import xml.etree.ElementTree as ET
import re
import xml.dom.minidom

def run():
    SSDP_ADDR = "239.255.255.250";
    SSDP_PORT = 1900;
    SSDP_MX = 1;
    SSDP_ST = "ssdp:all";


    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    ssdpRequest = createSSDPRequest(SSDP_ADDR, SSDP_PORT, SSDP_MX, SSDP_ST)
    s.sendto(ssdpRequest, (SSDP_ADDR, SSDP_PORT))

    while 1:
        data, addr = s.recvfrom(1024)
        print '\n\nReceived a Datagram from a Device'
        datalines = data.split('\n')
        for line in datalines:
            if line != '\r':
                print repr(line)
            loc = line.find('LOCATION:')
            if loc == 0:#start of string
                deviceURL = line[10:]
                urlParse = urlparse(deviceURL)
                deviceHostname = urlParse.hostname
                print "Device Hostname: " + deviceHostname
                devicePort = urlParse.port
                print "Device Port: " + str(devicePort)
                device = sendDeviceRequest(deviceURL)
                printDeviceInfo(device)
                serviceName = 'AVTransport'
                controlLocation = getControlURLForServiceFromDevice(serviceName, device)
                print 'Control Location: ' + controlLocation
                controlURL = 'http://' + deviceHostname + ':' + str(devicePort) + controlLocation
                print 'Control URL: ' + controlURL
                mediaLocation = 'http://10.0.1.9:8000/01%20Never%20Gonna%20Give%20You%20Up.mp3'
                loadMediaRequest = createLoadMediaRequest(mediaLocation)
                print 'Load Media Request: '
                prettyPrintXMLString(loadMediaRequest)
                sendLoadMediaRequest(loadMediaRequest, deviceHostname, devicePort, controlLocation)
                playMediaRequest = createPlayMediaRequest()
                print 'Play Media Request: '
                prettyPrintXMLString(playMediaRequest)
               
                playRes = sendPlayMediaRequest(playMediaRequest, deviceHostname, devicePort, controlLocation)
                

'''UDP and TCP Requests'''
def createSSDPRequest(SSDP_ADDR, SSDP_PORT, SSDP_MX, SSDP_ST):
    return "M-SEARCH * HTTP/1.1\r\n" + \
           "HOST: %s:%d\r\n" % (SSDP_ADDR, SSDP_PORT) + \
           "MAN: \"ssdp:discover\"\r\n" + \
           "MX: %d\r\n" % (SSDP_MX, ) + \
           "ST: %s\r\n" % (SSDP_ST, ) + "\r\n";

def sendDeviceRequest(deviceURL):
    print 'Requesting: ' + deviceURL
    res = urllib2.urlopen(deviceURL)
    print 'Response Headers'
    print res.info()
    responseBody = res.read()
    #strip the xml namespace
    xmlString = re.sub(' xmlns="[^"]+"', '', responseBody, count=1)
    #returns the root node of the etree
    root = ET.fromstring(xmlString)
#    print 'root.tag: ' + root.tag
#    print 'root.attrib: ' 
#    for key, value in root.attrib:
#        print 'key: ' + key + ' value: ' + value
    device = 0
    for child in root:
#        print 'child.tag: ' + child.tag
        if child.tag == 'device':
#            print 'found device'
            device = child
    
    
#    print 'device tag: ' + device.tag
    res.close()
    return device

'''Functions for Parsing device XML tree'''
def getControlURLForServiceFromDevice(serviceName, device):
    serviceList = getServiceListFromDevice(device)
    controlURL =  getControlURLForServiceFromServiceList(serviceName, serviceList)
    return controlURL

def getServiceListFromDevice(device):
    for child in device:
        if child.tag == 'serviceList':
            return child
    print 'Can\'t find service list in device'

def getControlURLForServiceFromServiceList(serviceName, serviceList):
    service = findServiceInServiceList(serviceName, serviceList)
    controlURL = getControlURLFromService(service)
    return controlURL

def findServiceInServiceList(serviceName, serviceList):
    for service in serviceList:
        for child in service:
            if child.tag == 'serviceType':
                if child.text.find(serviceName) != -1:
                    return service

def getControlURLFromService(service):
    for child in service:
        if child.tag == 'controlURL':
            return child.text
                    
def printDeviceInfo(device):
    print 'Device info from XML Response'
    for child in device:
        if child.tag == 'friendlyName':
            print 'Device Name: ' + child.text
        elif child.tag == 'deviceType':
            print 'Device Type: ' + child.text
        elif child.tag == 'manufacturer':
            print 'Manufacturer: ' + child.text
        elif child.tag == 'modelName':
            print 'Model Name: ' + child.text
        elif child.tag == 'modelNumber':
            print 'Model Number: ' + child.text


'''the section is for playing media files'''
def sendLoadMediaRequest(loadMediaRequest, host, port, location):
    opener = urllib2.build_opener()
    url = 'http://' + host + ':' + str(port) + location
    print 'sending load media request to: ' + url
    try:
        req = urllib2.Request(url, \
                           data=loadMediaRequest,\
                           headers={'Content-Type':'text/xml', 'SOAPAction':'"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"'})
        res = opener.open(req) 
        return res
    except Exception, e:
        if e.getcode() == 500:
            print 'Error Response'
            content = e.read()
            prettyPrintXMLString(content)
        else:
            raise 

def createLoadMediaRequest(mediaLocation):
    return '<?xml version="1.0" encoding="utf-8"?>' + \
           '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">' + \
                '<s:Body>' + \
                    '<u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">' + \
                        '<InstanceID>0</InstanceID>' + \
                        '<CurrentURI><![CDATA[' + mediaLocation + ']]></CurrentURI>' + \
                        '<CurrentURIMetaData></CurrentURIMetaData>' + \
                    '</u:SetAVTransportURI>' + \
                '</s:Body>' + \
            '</s:Envelope>'

def sendPlayMediaRequest(playMediaRequest, host, port, location):
    opener = urllib2.build_opener()
    try:
        req = urllib2.Request('http://' + host + ':' + str(port) + location, \
                           data=playMediaRequest,\
                           headers={'Content-Type':'text/xml', 'SOAPAction':'"urn:schemas-upnp-org:service:AVTransport:1#Play"'})
        res = opener.open(req) 
        return res 
    except Exception, e:
        if e.getcode() == 500:
            print 'Error Response'
            content = e.read()
            prettyPrintXMLString(content)
        else:
            raise

def createPlayMediaRequest():
    return '<?xml version="1.0" encoding="utf-8"?>' + \
                '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">' + \
                    '<s:Body>' +\
                        '<u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">' + \
                            '<InstanceID>0</InstanceID>' + \
                            '<Speed>1</Speed>' + \
                        '</u:Play>' + \
                    '</s:Body>' + \
                '</s:Envelope>'

def sendPauseMediaRequest(playMediaRequest, host, port, location):
    opener = urllib2.build_opener()
    try:
        req = urllib2.Request('http://' + host + ':' + str(port) + location, \
                           data=playMediaRequest,\
                           headers={'Content-Type':'text/xml', 'SOAPAction':'"urn:schemas-upnp-org:service:AVTransport:1#Pause"'})
        res = opener.open(req)
        return res
    except Exception, e:
        if e.getcode() == 500:
            print 'Error Response'
            content = e.read()
            prettyPrintXMLString(content)
        else:
            raise

def createPauseMediaRequest():
    return '<?xml version="1.0" encoding="utf-8"?>' + \
                '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">' + \
                    '<s:Body>' +\
                        '<u:Pause xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">' + \
                            '<InstanceID>0</InstanceID>' + \
                            '<Speed>1</Speed>' + \
                        '</u:Pause>' + \
                    '</s:Body>' + \
                '</s:Envelope>'

def prettyPrintXMLString(xmlString):
                xmlObj = xml.dom.minidom.parseString(xmlString)
                print xmlObj.toprettyxml().replace('\n\n', '\n').replace('\n\n', '\n')

run()
