from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import *
from krita import *
from datetime import *
import calendar
import os
import re
import time
import xml.parsers.expat
import asyncio

instance = Krita.instance()

class CopyDocInfo(Extension):
	
	outputFileName = 'output.txt'
	pattern = r'%\s*([^\s%]+)(?:\s*?\[([^%"]*?)\])?(?:\s*?([^\s%"\[\]]+?))?(?:\s*?"([^%"]*?)")?\s*?%'
	
	def __init__(self, parent):
		super().__init__(parent)
	
	def setup(self):
		pass
	
	def createActions(self, window):
		action = window.createAction('docinfo', 'Copy Document Infomation', 'tools/script')
		action.triggered.connect(self.triggered)
	
	def existsOutput(self, fileName = None):
		
		if not fileName:
			fileName = CopyDocInfo.outputFileName
		
		outputPath = os.path.join(os.path.dirname(__file__), fileName)
		
		if os.path.isfile(outputPath):
			return outputPath
		else:
			return False
		
	
	def getOutput(self, fileName = None):
		
		outputPath = self.existsOutput(fileName)
		
		if outputPath:
			outputFileHandle = open(outputPath, encoding='utf-8')
			output = outputFileHandle.read()
			outputFileHandle.close()
		else:
			output = ''
		
		return output
	
	def setOutput(self, content = '', fileName = None):
		
		outputPath = self.existsOutput(fileName)
		
		outputFileHandle = open(outputPath, mode='w', encoding='utf-8')
		outputFileHandle.write(content)
		outputFileHandle.close()
		
	
	def output(self, pre = ''):
		
		doc = Krita.instance().activeDocument()
		
		if doc:
			
			di = di0 = doc.documentInfo()
			
			parser = xml.parsers.expat.ParserCreate()
			
			output = pre if type(pre) is str and pre else self.getOutput()
			
			data = {
				'raw': di,
				'color-depth': doc.colorDepth(),
				'color-model': doc.colorModel(),
				'color-profile': doc.colorProfile(),
				'file-name': doc.fileName(),
				'height': doc.height(),
				'name': doc.name(),
				'resolution': doc.resolution(),
				'width': doc.width(),
				'x-offset': doc.xOffset(),
				'x-res': doc.xRes(),
				'y-offset': doc.yOffset(),
				'y-res': doc.yRes()
				# GroupLayer に findChildNodes 属性がないと言うエラーが通知される。恐らく最新バージョンでは使える？
				#'total-layers': len(doc.rootNode().findChildNodes(recursive = True))
			}
			currentKey = ''
			attr = None
			
			def parseStart(name, attribute):
				nonlocal currentKey, attr
				currentKey = name
				attr = attribute if type(attribute) is dict else {}
			
			def parseEnd(name):
				nonlocal currentKey, attr
				currentKey = ''
				attr = None
			
			def charData(text):
				
				nonlocal output, currentKey, doc
				
				text = text.strip(' \t\n\r')
				
				if currentKey and text:
					
					if currentKey in data:
						if isinstance(data[currentKey], list):
							attr['$'] = text
							data[currentKey].append(attr)
						else:
							data[currentKey]['$'] += text
					else:
						attr['$'] = text
						data[currentKey] = [ attr ] if currentKey == 'contact' else attr
			
			parser.StartElementHandler = parseStart
			parser.EndElementHandler = parseEnd
			parser.CharacterDataHandler = charData
			parser.Parse(di, True)
			
			if 'editing-cycles' in data:
				v = data['editing-cycles']['$']
				v0 = data['editing-cycles']['$'] = str(int(v) - 1)
				doc.setDocumentInfo(di0.replace('<editing-cycles>' + v + '</editing-cycles>', '<editing-cycles>' + v0 + '</editing-cycles>'))
			
			if 'editing-time' in data:
				v = data['editing-time']['$'] if data['editing-time']['$'] else 0
				data['editing-time']['$$'] = self.getDelta(int(v) * 1000000)
				data['editing-time']['$$'].update(self.getDate(int(v), True))
				data['editing-time']['$$']['raw'] = data['editing-time']['$'] = v
			
			if 'date' in data:
				v = data['date']['$'] if data['date']['$'] else 0
				data['date']['$$'] = self.getDate(v)
				data['date']['$$'].update(self.getDelta(data['date']['$$']['tt']))
				data['date']['$$']['raw'] = data['date']['$'] = v
			
			if 'creation-date' in data:
				v = data['creation-date']['$'] if data['creation-date']['$'] else 0
				data['creation-date']['$$'] = self.getDate(v)
				data['creation-date']['$$'].update(self.getDelta(data['creation-date']['$$']['tt']))
				data['creation-date']['$$']['raw'] = data['date']['creation-date'] = v
			
			while True:
				matched = re.search(self.pattern, output)
				if matched:
					k = matched.group(1)
					if k and k in data:
						
						v = data[k]
						
						if isinstance(v, list):
							i = matched.group(3)
							l = len(v)
							if i:
								i = int(i)
								i = i if i < l else l - 1
								i = l + i if i < 0 else i
								i = 0 if i < 0 else i
								v = v[i] if i < l else ''
						
						if isinstance(v, list) is False:
							v = [ v ]
						
						l = len(v)
						values = []
						for i in range(l):
							
							v0 = v[i]
							
							if type(v0) is dict:
								attrName = matched.group(2)
								v0 = v0[attrName] if attrName and attrName in v0 else v0
								if type(v0) is dict:
									if '$$' in v0:
										v0 = v0['$$']
										if type(v0) is dict:
											v0 = v0[matched.group(3)] if matched.group(3) else v0['raw']
									else:
										v0 = v0['$'] if '$' in v0 else ''
							if matched.group(4):
								v0 = ('{0:' + matched.group(4) + '}').format(int(v0))
							
							values.append(str(v0))
							
						output = output[:matched.start()] + '\n'.join(values) + output[matched.end():]
							
					else:
						output = output[:matched.start()] + output[matched.end():]
				else:
					break
			
			return output
		
	
	def copyDocumentInformation(self, pre = ''):
			
		# Just for the debugging
		QGuiApplication.clipboard().setText('FAILED_TO_COPY_DOCUMENT_INFORMATION')
		
		QGuiApplication.clipboard().setText(self.output(pre))
	
	def triggered(self):
		
		self.copyDocumentInformation()
	
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

class CopyDocInfoDocker(DockWidget):
	
	getActiveDocumentTimeout = 5000.0
	
	def __init__(self):
		
		super().__init__()
		
		self.setWindowTitle('Doc Info')
		mainWidget = QWidget(self)
		self.setWidget(mainWidget)
		
		self.instance = Krita.instance()
		self.instanceNotifier = self.instance.notifier()
		
		self.instanceNotifier.imageCreated.connect(self.createdImage)
		self.instanceNotifier.imageClosed.connect(self.closedImage)
		
		self.setExtension(copyDocInfo)
		
		self.mainLayout = QVBoxLayout()
		
		self.rootLayout = QBoxLayout(QBoxLayout.TopToBottom)
		mainWidget.setLayout(self.rootLayout)
		
		self.tabs = QTabWidget()
		# createdImage, closedImage の発生後に Krita.instance().activeDocument() を取得できないため（恐らく Krita の仕様）
		# それらのシグナルと同期してプレビュータブを更新する機能は未使用にしている。
		# self.tabs.currentChanged.connect(self.changedTab)
		
		self.editTab = QWidget()
		self.editTabLayout = QVBoxLayout()
		self.editTab.setLayout(self.editTabLayout)
		
		self.editControlLayout = QHBoxLayout()
		self.editEditLayout = QVBoxLayout()
		
		self.copyButton = QPushButton('Copy')
		self.copyButton.setEnabled(False)
		self.copyButton.clicked.connect(self.clickedCopyButton)
		
		output = self.extension.getOutput()
		
		self.saveButton = QPushButton('Save')
		self.saveButton.setEnabled(False)
		self.saveButton.clicked.connect(self.clickedSaveButton)
		
		self.clearButton = QPushButton('Clear')
		self.clearButton.clicked.connect(self.clickedClearButton)
		
		self.editControlLayout.addWidget(self.copyButton)
		self.editControlLayout.addWidget(self.saveButton)
		# self.editControlLayout.addWidget(self.clearButton)
		
		self.textEdit = QPlainTextEdit()
		self.textEdit.setPlainText(output)
		self.textEdit.textChanged.connect(self.changedText)
		self.lastOutput = self.textEdit.toPlainText()
		
		self.editEditLayout.addWidget(self.textEdit)
		
		self.editTabLayout.addLayout(self.editControlLayout)
		self.editTabLayout.addLayout(self.editEditLayout)
		
		self.previewTab = QWidget()
		self.previewTabLayout = QVBoxLayout()
		self.previewTab.setLayout(self.previewTabLayout)
		
		self.previewControlLayout = QHBoxLayout()
		self.previewEditLayout = QVBoxLayout()
		
		self.previewCopyButton = QPushButton('Copy')
		self.previewCopyButton.clicked.connect(self.clickedPreviewCopyButton)
		
		self.previewUpdateButton = QPushButton('Update')
		self.previewUpdateButton.setEnabled(False)
		self.previewUpdateButton.clicked.connect(self.clickedPreviewUpdateButton)
		
		self.previewControlLayout.addWidget(self.previewCopyButton)
		self.previewControlLayout.addWidget(self.previewUpdateButton)
		
		self.previewText = QPlainTextEdit()
		
		self.previewEditLayout.addWidget(self.previewText)
		
		self.previewTabLayout.addLayout(self.previewControlLayout)
		self.previewTabLayout.addLayout(self.previewEditLayout)
		
		self.tabs.addTab(self.editTab, 'Edit')
		self.tabs.addTab(self.previewTab, 'Preview')
		
		self.mainLayout.addWidget(self.tabs)
		
		mainWidget.layout().addLayout(self.mainLayout)
	
	async def getActiveDocument(self):
		begin = time.time()
		while True:
			doc = self.instance.activeDocument()
			if doc:
				return doc
			elif (time.time() - begin) >= self.getActiveDocumentTimeout:
				return None
			await asyncio.sleep(16)
	
	def clickedPreviewUpdateButton(self):
		self.previewText.setPlainText(self.extension.output(self.textEdit.toPlainText()))
	
	def clickedPreviewCopyButton(self):
		self.extension.copyDocumentInformation(self.previewText.toPlainText())
	
	def changedTab(self):
		if self.tabs.currentWidget() is self.previewTab and len(self.instance.documents()):
		# if self.tabs.currentWidget() is self.previewTab and asyncio.run(self.getActiveDocument()):
			self.previewText.setPlainText(self.extension.output(self.textEdit.toPlainText()))
	
	def createdImage(self):
		self.copyButton.setEnabled(True)
		self.previewUpdateButton.setEnabled(True)
		# self.changedTab()
	
	def closedImage(self):
		if not len(self.instance.documents()):
			self.copyButton.setEnabled(False)
			self.previewUpdateButton.setEnabled(False)
	
	def clickedCopyButton(self):
		self.extension.copyDocumentInformation()
	
	def clickedSaveButton(self):
		plainText = self.textEdit.toPlainText()
		if self.lastOutput != plainText:
			self.lastOutput = plainText
			self.extension.setOutput(plainText)
			self.saveButton.setEnabled(False)
	
	def clickedClearButton(self):
		self.textEdit.setPlainText('')
	
	def changedText(self):
		if self.lastOutput == self.textEdit.toPlainText():
			self.saveButton.setEnabled(False)
		else:
			self.saveButton.setEnabled(True)
	
	def canvasChanged(self, canvas):
		pass
	
	def setExtension(self, extension):
		if isinstance(extension, CopyDocInfo):
			self.extension = extension

copyDocInfo = CopyDocInfo(instance)
instance.addExtension(copyDocInfo)
copyDocInfoDocker = DockWidgetFactory('cooyDocInfo', DockWidgetFactoryBase.DockRight, CopyDocInfoDocker)
instance.addDockWidgetFactory(copyDocInfoDocker)