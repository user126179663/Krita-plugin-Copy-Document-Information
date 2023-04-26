from PyQt5.QtWidgets import *
from krita import *
from datetime import *
import xml.parsers.expat

class CopyDocInfo(Extension):

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
			cb = QGuiApplication.clipboard()
			di = doc.documentInfo()
			parser = xml.parsers.expat.ParserCreate()
			
			targets = {
				'title': { 'prefix': '「', 'suffix': '」', 'type': 'str' },
				'subject': { 'prefix': ' ℹ️ ', 'suffix': '', 'type': 'str' },
				'license': { 'prefix': ' ©️ ', 'suffix': '', 'type': 'str' },
				'abstract': { 'prefix': '\n\n', 'suffix': '\n', 'type': 'str' },
				'linebreak': '\n',
				'editing-cycles': { 'prefix': '🎨 ', 'suffix': ' ', 'type': 'str' },
				'editing-time': { 'prefix': '⏱ ', 'suffix': ' ', 'type': 'time' },
				'date': { 'prefix': '📝 ', 'suffix': ' ', 'type': 'date' },
				'creation-date': { 'prefix': '🚀 ', 'suffix': '', 'type': 'date' }
			}
			output = {}
			currentKey = ''
			
			def parseStart(name, attributes):
				nonlocal currentKey
				if name in targets:
					currentKey = name
				else:
					currentKey = ''
			
			def charData(text):
				
				nonlocal output
				nonlocal currentKey
				
				text = text.strip(' \t\n\r')
				str = ''
				
				if text is not '':
					
					if currentKey in targets:
						
						target = targets[currentKey]
						
						if target['type'] == 'time':
							date = datetime.fromtimestamp(int(text) * 1000)
							delta = timedelta(microseconds = int(text) * 1000)
							str = '{0}{1}日{2}時間{3}分{5}'.format(target['prefix'], delta.days if delta.days else 0, date.hour if date.hour else 0, date.minute if date.minute else 0, date.second if date.second else 0, target['suffix'])
						
						elif target['type'] == 'date':
							date = datetime.fromisoformat(text)
							str = '{0}{1}/{2:02d}/{3:02d} {4:02d}:{5:02d}{7}'.format(target['prefix'], date.year, date.month, date.day, date.hour, date.minute, date.second, target['suffix'])
						
						else:
							str = '{0}{1}{2}'.format(target['prefix'], text, target['suffix'])
					
					if currentKey in output:
						output[currentKey] += str
					else:
						output[currentKey] = str
			
			parser.StartElementHandler = parseStart
			parser.CharacterDataHandler = charData
			parser.Parse(doc.documentInfo(), True)
			
			result = ''
			for k in targets:
				if type(targets[k]) is str:
					result += targets[k]
					continue
				for k0 in output:
					if k == k0:
						result += output[k]
			
			cb.setText(result)

Krita.instance().addExtension(CopyDocInfo(Krita.instance()))