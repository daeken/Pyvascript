import imp
from Transformana import Macro, TransformNodes
import Transformana as ta

class CodeBuilder(object):
	def __init__(self, top):
		self.locals = None
		self.localsStack = []

		self.inClass = None

		lines = self.emit(top).split('\n')
		newLines = []
		for line in lines:
			if line.strip() == '':
				continue

			if line.rstrip()[-1] in '{}':
				newLines.append(line)
			else:
				newLines.append(line + ';')
		self.buffer = '\n'.join(newLines)

	def emit(self, node):
		if isinstance(node, ta.Exp):
			buffer = ''
			for exp in self.transformNode(node):
				buffer += self.emit(exp)
			return buffer
		elif isinstance(node, str):
			return node
		elif isinstance(node, tuple):
			return '(' + ', '.join(map(self.emit, node)) + ')'
		elif isinstance(node, list):
			type, rest = node[0], node[1:]
			if type == 'block' or type == 'blockWithBraces':
				return self.emitBlock(braces=type == 'blockWithBraces', *rest)
			elif type == 'dict':
				return '{' + ', '.join(self.emit(name) + ' : ' + self.emit(value) for name, value in rest) + '}'
			elif type == 'expr':
				ret = ' '.join(map(self.emit, rest))
				if self.inClass != None:
					return ret + ';\n'
				else:
					return ret
			elif type == 'list':
				return '[' + ', '.join(map(self.emit, rest)) + ']'
			elif type == 'top':
				return self.emitBlock(None, rest, braces=None)
			else:
				print 'Unknown JS node type:', type
				return ''

	def emitBlock(self, head, body, braces=False):
		head = self.emit(head)
		if braces == None:
			head = ''
			end = '\n'
		#elif braces or len(body) != 1:
		else:
			head += ' {\n'
			end = '}\n'
		#else:
		#	head += '\n'
		#	end = '\n'

		if braces == None:
			indent = ''
		else:
			indent = '\t'
		bodyStr = ''
		for elem in map(self.emit, body):
			if '\n' in elem: # Block
				lines = elem.split('\n')
				for line in lines:
					bodyStr += indent + line + '\n'
			else:
				bodyStr += indent + elem + '\n'

		return '\n' + head + bodyStr + end

	assignOps = dict(
			OP_ASSIGN='='
		)
	def transformNode(self, node):
		type, node = node[0], node[1:]
		if False: # No-op to allow the rest to be elifs
			pass

		elif type == 'add':
			left, right = node[0]
			yield (['expr', left, '+', right], )

		elif type == 'assign':
			left, right = node
			assert len(left) == 1
			left = left[0]

			if left[0] == 'assname':
				leftName = left[1]
				op = left[2]
				if self.locals == None:
					self.locals = []
				if leftName in self.locals:
					left = leftName
				else:
					self.locals.append(leftName)
					left = 'var ' + leftName
			elif left[0] == 'assattr':
				left, op = ta.Getattr(left[1], left[2]), left[3]
			elif left[0] == 'asstuple':
				if self.locals == None:
					self.locals = []
				name = '__tuple_temp'
				if name not in self.locals:
					self.locals.append(name)
					name = 'var __tuple_temp'
				yield ['expr', name, '=', right, ';']

				for i, (_, var, __) in enumerate(left[1]):
					if var not in self.locals:
						self.locals.append(var)
						var = 'var ' + var
					yield ['expr', var, '=', '__tuple_temp[', str(i), ']', ';']
				return
			elif left[0] == 'subscript':
				base, op, subscr = left[1:]
				left = ta.Subscript(base, None, subscr)
			else:
				print 'Unknown assignment type:', left[0]
				print left[1:]

			yield ['expr', left, self.assignOps[op], right, ';']

		elif type == 'augassign':
			left, op, right = node
			yield ['expr', left, op, right]

		elif type == 'break':
			yield ['expr', 'break']

		elif type == 'callfunc':
			name, args, _, __ = node

			if name == ['name', 'isinstance']:
				yield ['expr', args[0], 'instanceof', args[1]]
				return

			newArgs = []
			kwargs = []
			for arg in args:
				if arg[0] == 'keyword':
					kwargs.append((`arg[1]`, arg[2]))
				else:
					newArgs.append(arg)

			if len(kwargs):
				newArgs.append(['dict'] + kwargs)

			if name == ['name', 'dict']:
				yield newArgs[0]
			else:
				yield ['expr', name, tuple(newArgs)]

		elif type == 'class':
			name, supers, _, body, __ = node
			if supers != None and len(supers):
				assert len(supers) == 1
				superCls = supers[0]
			else:
				superCls = None

			saved, self.inClass = self.inClass, (name, superCls)
			yield body
			self.inClass = saved

		elif type == 'compare':
			left, rest = node
			assert len(rest) == 1

			comp, right = rest[0]
			if comp == 'not in':
				yield ['expr', '!', (['expr', left, 'in', right], )]
			else:
				yield ['expr', left, comp, right]

		elif type == 'const':
			if node[0] == None:
				yield 'null'
			else:
				yield `node[0]`

		elif type == 'dict':
			elems = node[0]
			yield ['dict'] + elems

		elif type == 'discard':
			yield node[0]

		elif type == 'for':
			left, right, body, _ = node
			left = left[1]
			if right[0] == 'callfunc' and right[1] == ['name', 'range']:
				forStmt = ['expr', 'var', left, ' = 0;', left, '<', right[2][0], ';', left, '++']
			else:
				forStmt = ['expr', 'var', left, 'in', right]
			yield ['block', ['expr', 'for', (forStmt, )], body[1]]

		elif type == 'function':
			_, name, argNames, defaults, flags, doc, code = node
			self.localsStack.append(self.locals)
			if self.locals != None:
				self.locals = self.locals + list(argNames)
			else:
				self.locals = list(argNames)

			init = []
			off = len(argNames)-len(defaults)
			for i in range(len(defaults)):
				aname = argNames[off+i]
				init.append(['expr', 'var', aname, '=', '(typeof(', aname, ') == \'undefined\')?', defaults[i], ':', aname])

			code[1] = init + code[1]
			if self.inClass == None:
				yield ['blockWithBraces', ['expr', 'function', name, tuple(argNames)], code[1]]
			else:
				argNames = tuple(argNames[1:])
				(cls, superCls), self.inClass = self.inClass, None
				if name == '__init__':
					yield ['blockWithBraces', ['expr', 'function', cls, argNames], code[1]]
					self.inClass = (cls, superCls)
					if superCls != None:
						yield ['expr', cls + '.prototype', '=', 'new', superCls, ()]
				else:
					yield ['blockWithBraces', ['expr', cls + '.prototype.' + name, '=', 'function', argNames], code[1]]
					self.inClass = (cls, superCls)

			self.locals = self.localsStack.pop()

		elif type == 'getattr':
			if node[1] == 'new':
				yield ['expr', 'new', node[0]]
			else:
				yield ['expr', node[0], '.', node[1]]
		
		elif type == 'global':
			self.locals += node[0]

		elif type == 'if':
			cases, otherwise = node

			for i, (cond, body) in enumerate(cases):
				type = 'if' if i == 0 else 'else if'
				yield ['block', ['expr', type, (cond, )], body[1]]

			if otherwise != None:
				yield ['block', 'else', otherwise[1]]

		elif type == 'import':
			imps, = node
			for moduleName, _ in imps:
				fp, fn, _ = imp.find_module(moduleName)
				code = fp.read()
				code = ElementMacro.fromCode(code)
				code = UriOfMacro.fromCode(code)
				yield code

		elif type == 'list':
			elems = node[0]
			yield ['list'] + elems

		elif type == 'mod':
			left, right = node[0]
			yield (['expr', left, '%', right], )

		elif type == 'module':
			yield ['top', node[1]]

		elif type == 'mul':
			left, right = node[0]
			yield (['expr', left, '*', right], )

		elif type == 'name':
			if node[0] == 'True':
				yield 'true'
			elif node[0] == 'False':
				yield 'false'
			elif node[0] == 'None':
				yield 'null'
			elif node[0] == 'self':
				yield 'this'
			else:
				yield node[0]

		elif type == 'not':
			yield ['expr', '!(', node[0], ')']

		elif type == 'and':
			elems = ['expr', node[0][0]]
			for i in range(1, len(node[0])):
				elems += ['&&', node[0][i]]
			yield elems

		elif type == 'or':
			elems = ['expr', node[0][0]]
			for i in range(1, len(node[0])):
				elems += ['||', node[0][i]]
			yield elems

		elif type == 'pass':
			pass

		elif type == 'return':
			yield ['expr', 'return', node[0]]

		elif type == 'stmt':
			for exp in node[0]:
				yield exp

		elif type == 'sub':
			left, right = node[0]
			yield (['expr', left, '-', right], )

		elif type == 'subscript':
			name, op, sub = node
			sub = sub[0]
			yield ['expr', name, ['list', sub]]

		elif type == 'tuple':
			yield ['expr', ['list'] + node[0]]

		elif type == 'unarysub':
			yield ['expr', '-', node[0]]

		elif type == 'while':
			head, body, _ = node
			yield ['block', ['expr', 'while', (head, )], body[1]]

		else:
			print 'Unknown node type:', type
			import pprint
			pprint.pprint(node)

@Macro
def Javascript(ast):
	cb = CodeBuilder(ast)

	return cb.buffer

@TransformNodes('name')
def ElementMacro(ast):
	if ast == ['name', '_']:
		return ta.Name('$')

def expToRoute(exp):
	if exp[0] == 'name':
		return exp[1], 'index'
	elif exp[0] == 'getattr':
		return exp[1][1], exp[2]

from pylons import url
@TransformNodes('callfunc')
def UriOfMacro(ast):
	if ast[1] != ['name', '_uriOf']:
		return

	kwargs = dict()
	controller = ast[2][0]
	if controller[0] == 'callfunc':
		for _, name, value in controller[2]:
			assert value[0] == 'const'
			kwargs[name] = value[1]
		controller, action = expToRoute(controller[1])
	else:
		controller, action = expToRoute(controller)

	if controller.endswith('Controller'):
		controller = controller.rstrip('Controller')

	return ta.Const(url(controller=controller, action=action, **kwargs))

from jsmin import JavascriptMinify
from cStringIO import StringIO
def compileString(code, minify=True):
	code = ElementMacro.fromCode(code)
	code = UriOfMacro.fromCode(code)
	code = Javascript.fromCode(code)
	
	if minify:
		jsm = JavascriptMinify()
		out = StringIO()
		jsm.minify(StringIO(code), out)
		code = out.getvalue()
	
	return code.strip()

if __name__=='__main__':
	@Javascript
	def jsTest(a, b):
		alert('Hello world!')

		foo = 5
		foo = 6
		bar = 'Hi!'

		if a == 5:
			alert('Five!')
			b = 5
		elif a == 6:
			alert('Six')
		else:
			alert('Hmm')

		return 5

	print jsTest
