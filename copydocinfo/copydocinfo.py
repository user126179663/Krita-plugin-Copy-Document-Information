from PyQt5.QtWidgets import *
from krita import *
from datetime import *
import calendar
import os
import re
import time
import xml.parsers.expat

class CopyDocInfo(Extension):
	
	pattern = r'%\s*([^\s%]+)(?:\s*?([^\s%"]+?))?(?:\s*?"([^%"]*?)")?\s*?%'
	
	def __init__(self, parent):
		super().__init__(parent)
	
	def setup(self):
		pass
	
	def createActions(self, window):
		action = window.createAction('docinfo', 'Copy Document Infomation', 'tools/script')
		action.triggered.connect(self.copyDocumentInformation)
	
	def copyDocumentInformation(self):
		
		doc = Krita.instance().activeDocument()
		
		if doc is not None:
			
			di = di0 = doc.documentInfo()
			
			parser = xml.parsers.expat.ParserCreate()
			
			dirname = os.path.dirname(__file__)
			outputPath = os.path.join(dirname, 'output.txt')
			
			QGuiApplication.clipboard().setText(outputPath)
			
			outputFileHandle = open(outputPath, encoding='utf-8')
			
			output = outputFileHandle.read()
			
			outputFileHandle.close()
			
			data = { 'raw': di }
			currentKey = ''
			
			def parseStart(name, attributes):
				nonlocal currentKey
				currentKey = name
			
			def parseEnd(name):
				nonlocal currentKey
				currentKey = ''
			
			def charData(text):
				
				nonlocal output, currentKey, doc
				
				text = text.strip(' \t\n\r')
				
				if currentKey is not '' and text is not '':
					
					if currentKey in data:
						data[currentKey] += text
					else:
						data[currentKey] = text
			
			parser.StartElementHandler = parseStart
			parser.EndElementHandler = parseEnd
			parser.CharacterDataHandler = charData
			parser.Parse(di, True)
			
			if 'editing-cycles' in data:
				v = data['editing-cycles']
				v0 = data['editing-cycles'] = str(int(v) - 1)
				doc.setDocumentInfo(di0.replace('<editing-cycles>' + v + '</editing-cycles>', '<editing-cycles>' + v0 + '</editing-cycles>'))
			
			if 'editing-time' in data:
				v = data['editing-time'] if data['editing-time'] else 0
				data['editing-time'] = self.getDelta(int(v) * 1000)
				data['editing-time'].update(self.getDate(int(v), True))
				data['editing-time']['raw'] = v
			
			if 'date' in data:
				v = data['date'] if data['date'] else 0
				data['date'] = self.getDate(v)
				data['date'].update(self.getDelta(data['date']['tt']))
				data['date']['raw'] = v
			
			if 'creation-date' in data:
				v = data['creation-date'] if data['creation-date'] else 0
				data['creation-date'] = self.getDate(v)
				data['creation-date'].update(self.getDelta(data['date']['tt']))
				data['creation-date']['raw'] = v
			
			while True:
				matched = re.search(self.pattern, output)
				if matched:
					k = matched.group(1)
					if k and k in data:
						v = data[k]
						if type(v) is not str:
							v = v[matched.group(2)] if matched.group(2) else v['raw']
						if matched.group(3):
							v = ('{0:' + matched.group(3) + '}').format(int(v))
						output = output[:matched.start()] + str(v) + output[matched.end():]
					else:
						output = output[:matched.start()] + output[matched.end():]
				else:
					break
			
			QGuiApplication.clipboard().setText(output)
	
	def getDate(self, string, asUTC = False):
		date = datetime.fromisoformat(string) if type(string) is str else datetime.fromtimestamp(int(string))
		if asUTC:
			utc = int(time.mktime(date.timetuple()) - (datetime.fromtimestamp(0) - datetime(1970,1,1)).total_seconds())
			if utc < 0:
				utc = 0
			date = datetime.fromtimestamp(int(time.mktime(date.timetuple()))) - (datetime.fromtimestamp(0) - datetime(1970,1,1))
		else:
			utc = int(time.mktime(date.timetuple()))
		
		data = {
			'date': date,
			'raw-date': string,
			'y': date.year,
			'M': date.month,
			'd': date.day,
			'h': date.hour,
			'm': date.minute,
			's': date.second,
			'ms': int(date.microsecond / 1000),
			'mcs': date.microsecond,
			'T': utc,
			't': utc * 1000 + int(date.microsecond / 1000),
			'tt': utc * 1000000 + date.microsecond
		}
		return data
	
	def getDelta(self, time):
		delta = timedelta(microseconds = int(time))
		data = {
			'delta': delta,
			'raw-time': time,
			'days': delta.days,
			'seconds': delta.seconds,
			'milliseconds': int(delta.microseconds / 1000),
			'microseconds': delta.microseconds
		}
		return data

instance = Krita.instance()

instance.addExtension(CopyDocInfo(instance))