class TableHelper:
	def __init__(self, id):
		self.table = id
	
	def addRow(self, cells):
		data = '<tr>'
		for i in cells:
			data += '<td>' + cells[i] + '</td>'
		data += '</tr>'
		
		_('#' + self.table + ' > tbody:last').append(data)

class PaginationHelper:
	def __init__(self, id, divId, perPage, title=""):
		self.table = id
		self.div = divId
		self.perPage = perPage
		self.count = 0
		self.title = title
		if self.title != "":
			self.title = self.title + " - "
		self.data = []
		
		self.addedHeader = False
		self.offset = 0
	
	def addRow(self, cells):
		data = '<tr>'
		for i in cells:
			data += '<td>' + cells[i] + '</td>'
		data += '</tr>'
		
		self.data[self.data.length] = data
		self.count += 1
	
	def render(self):
		if not self.addedHeader:
			self.addHeader()
			self.addedHeader = True
		
		_('#' + self.table).find('tr:not(:first)').remove()
		
		for i in range(Math.min(self.perPage, self.count - self.offset)):
			_('#' + self.table + ' > tbody:last').append(self.data[self.offset + i])
	
	def addHeader(self):
		if self.count <= self.perPage:
			return
		
		_('#' + self.div).prepend(self.buildHeader())
		if (self.div != "lockDiv"):
			_('#' + self.div).append(self.buildHeader())
		self.updateHeader()
	
	def buildHeader(self):
		header = '<table width="100">'
		header += '<tr><td width="15%" align="center"><a id="prev" href="#" class="arrow-previous">Previous</a></td><td width="70%" align="center" id="info" style="font-weight: bold"></td><td width="15%" align="center"><a id="next" href="#" class="arrow-next">Next</a></td></tr>'
		header += '</table>'
		elem = _(header)
		elem.css('width', _('#' + self.table).css('width'))
		elem.find('#prev').bind('click', dict(obj=self), self.prevPage)
		elem.find('#next').bind('click', dict(obj=self), self.nextPage)
		return elem
	
	def updateHeader(self):
		if self.count - self.offset > self.perPage:
			_('#' + self.div).find('#next').show()
		else:
			_('#' + self.div).find('#next').hide()
		if self.offset >= self.perPage:
			_('#' + self.div).find('#prev').show()
		else:
			_('#' + self.div).find('#prev').hide()
		
		end = Math.min(self.count, self.offset + self.perPage)
		info = self.title + 'Results ' + (self.offset + 1) + '-' + end + ' of ' + self.count
		_('#' + self.div).find('#info').html(info)
	
	def nextPage(self, evt):
		self_ = evt.data.obj
		self_.offset += self_.perPage
		self_.render()
		
		self_.updateHeader()
	def prevPage(self, evt):
		self_ = evt.data.obj
		self_.offset -= self_.perPage
		self_.render()
		
		self_.updateHeader()
