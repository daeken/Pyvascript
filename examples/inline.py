from Pyvascript import JavaScript
from AjaxHelper import *

@JavaScript
def test():
	alert('Test!')
	TestClass.new() # Notice the 'new'

class TestClass(JavaScript):
	def __init__(self):
		alert('TestClass created')
		self.reset()
	
	def reset(self):
		self.value = 0
	
	def inc(self):
		alert(self.value)
		self.value += 1
TestClass = TestClass()

class AjaxTest(AjaxHelper):
	def __init__(self):
		self.post('/some/url')
	
	def success(self, data):
		alert(data)
	
	def failure(self, o):
		alert('Ajax failure...')
AjaxTest = AjaxTest()

print '<script language="Javascript">'
print test
print TestClass
print AjaxTest
print '</script>'
