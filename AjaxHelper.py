class AjaxHelper:
	def __init__(self):
		self.timeout = null

	def call(self, uri, query):
		_self = self
		def callback(data, status):
			if status == 'success':
				#if isinstance(data, Array):
				#	_self.success.apply(_self, data)
				#else:
				_self.success(data)
			else:
				_self.failure()
		def error():
			_self.failure()

		_.ajaxSetup(timeout=self.timeout, error=error)
		_.post(uri, query, callback, 'json')


def ready():
	def ignore():
		return False
	_('form').submit(ignore)

_(document).ready(ready)
