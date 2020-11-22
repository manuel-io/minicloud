import requests
from xml.dom.minidom import parseString
from pathlib import Path
from mimetypes import MimeTypes
from config import app

class MiniDLNA:
    headers = { 'SOAPACTION': 'urn:schemas-upnp-org:service:ContentDirectory:1#Browse' }

    def __init__(self, host, auth, verify):
        app.logger.info('Connect to DLNA: %s%s' % (host, '/rootDesc.xml'))
        app.logger.info('Verification: %s' % verify)

        auth = { 'X-Auth-Token': auth }
        MiniDLNA.headers.update(auth)

        try:
            # Get Service ContentDirectory
            result = requests.get('%s%s' % (host, '/rootDesc.xml'), headers=auth, verify=verify)
            result.raise_for_status()

        except Exception as e:
            raise e

        root = parseString(result.content)
        services = list(map(lambda service: self.__parse_service(service), root.getElementsByTagName('service')))
        content = [ service for service in services if service['name'] == 'urn:schemas-upnp-org:service:ContentDirectory:1' ][0]
        request = '%s%s' % (host, content['url'])

        try:
            # Get Root of ContentDirectory
            result = requests.post(request, data=self.__get_object_id('0'), headers=MiniDLNA.headers, verify=verify)
            result.raise_for_status()

        except Exception as e:
            raise e

        root = parseString(result.content)

        self.verify = verify
        self.request = request
        self.body = parseString(root.getElementsByTagName('Result')[0].firstChild.nodeValue)

    def files(self):
        return self.__next(self.body, [])

    def __next(self, body, base):
        containers =  list(map(lambda container: self.__parse_container(container), body.getElementsByTagName('container')))
        items = list(map(lambda item: self.__parse_item(item, base), body.getElementsByTagName('item')))

        for container in containers:
            try:
                result = requests.post(self.request, data=self.__get_object_id(container['index']), headers=MiniDLNA.headers, verify=self.verify)
                result.raise_for_status()

            except Exception as e:
                app.logger.error('Error in MiniDLNA traverse files: %s' % str(e))
                continue

            root = parseString(result.content)
            body = parseString(root.getElementsByTagName('Result')[0].firstChild.nodeValue)
            items += self.__next(body, base + [container['title']])

        return items

    def __get_object_id(self, index):
        return '''
          <?xml version="1.0" encoding="utf-8"?>
            <s:Envelope xmlns:ns0="urn:schemas-upnp-org:service:ContentDirectory:1" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
              <s:Body>
                <ns0:Browse>
                  <ObjectID>%s</ObjectID>
                  <BrowseFlag>BrowseDirectChildren</BrowseFlag>
                  <Filter>*</Filter>
                </ns0:Browse>
              </s:Body>
            </s:Envelope>
          </xml>
        ''' % index

    def __parse_service(self, service):
        name = service.getElementsByTagName('serviceType')[0].firstChild.nodeValue
        url = service.getElementsByTagName('controlURL')[0].firstChild.nodeValue
        return { 'name': name
               , 'url': url
               }

    def __parse_container(self, container):
        index = container.getAttribute('id')
        title = container.getElementsByTagName('dc:title')[0].firstChild.nodeValue
        return { 'index': index
               , 'title': title
               }

    def __parse_item(self, item, base):
        index = item.getAttribute('id')
        title = item.getElementsByTagName('dc:title')[0].firstChild.nodeValue
        result = item.getElementsByTagName('res')[0]
        url = result.firstChild.nodeValue
        path = '/'.join(base + [title]) + Path(url).suffix
        return { 'index': index
               , 'title': title
               , 'size': result.getAttribute('size')
               , 'duration': result.getAttribute('duration')
               , 'bitrate': result.getAttribute('bitrate')
               , 'sampling': result.getAttribute('sampleFrequency')
               , 'channels': result.getAttribute('nrAudioChannels')
               , 'resolution': result.getAttribute('resolution')
               , 'url': url
               , 'path': path
               , 'mime': MimeTypes().guess_type(path)[0]
               }
