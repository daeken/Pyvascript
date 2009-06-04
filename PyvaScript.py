import compiler, dis, opcode, struct

class JsDict(dict):
	def __repr__(self):
		return '{%s}' % ', '.join('%s : %s' % kv for kv in self.items())

class JsList(list):
	def __repr__(self):
		return '[%s]' % ', '.join(map(str, self))

class JsFunc(object):
	def __init__(self, name, args=()):
		self.name = name
		self.args = tuple(args)
	
	def __str__(self):
		return '%s(%s)' % (self.name, ', '.join(self.args))
	def __repr__(self):
		return str(self)

class JavaScript(object):
	varcount = 0
	
	@classmethod
	def __new__(cls, *args, **kwargs):
		if cls == JavaScript:
			return object.__new__(cls, *args, **kwargs)
		
		superdir = dir(JavaScript)
		subdir = [elem for elem in dir(cls) if elem not in superdir]
		
		if cls.__init__ is not JavaScript.__init__:
			code = str(JavaScript(cls.__init__, inClass=True, fname=cls.__name__)).rstrip()[:-1].rstrip() + '\n'
		else:
			code = 'function %s() {\n' % cls.__name__
		
		for key in subdir:
			val = getattr(cls, key)
			if callable(val):
				continue
			
			code += '\tthis.%s = %s;\n' % (key, val)
		
		code += '}\n'
		
		for func in subdir:
			func = getattr(cls, func)
			if not callable(func):
				continue
			
			code += '%s.prototype.%s = %s' % (
				cls.__name__,
				func.__name__,
				str(JavaScript(func, inClass=True, anonymous=True))
			)
		
		return code
	
	def __init__(self, func, inClass=False, fname=None, anonymous=False):
		#dis.dis(func)
		self.opcdmap = JavaScript.opcode.func_defaults[0]
		self.code = func.func_code
		self.co_code = self.code.co_code
		
		self.hit = []
		pc = 0
		outer = []
		stack = []
		scope = [name for name in self.code.co_varnames[:self.code.co_argcount]]
		try:
			while pc != -1 and pc < len(self.co_code):
				pc = self.execute(pc, block=outer, stack=stack, scope=scope)
		except Exception:
			print
			import sys, traceback
			traceback.print_exc(file=sys.stdout)
			dis.dis(func)
			self.js = ''
			return
		
		if func.func_defaults:
			defaults = ''
			
			off = self.code.co_argcount - len(func.func_defaults)
			for i in xrange(len(func.func_defaults)):
				var = self.code.co_varnames[off+i]
				val = func.func_defaults[i]
				if val == None:
					val = 'null'
				else:
					if val is True:
						val = 'true'
					elif val is False:
						val = 'false'
					elif val is None:
						val = 'None'
					else:
						val = repr(val)
				defaults += '\t%s = (typeof(%s) != \'undefined\' && %s != null) ? %s : %s;\n' % (
						var, var, var, var, val
					)
		else:
			defaults = ''
		
		if fname == None:
			fname = func.__name__
		
		if fname == '__top__':
			self.js = '\n'.join(line for line in outer if line != 'return;')
		else:
			self.js = \
'''
function%s(%s) {
%s%s
}
''' % (
				(not anonymous) and ' %s' % fname or '',
				', '.join(self.code.co_varnames[inClass and 1 or 0:self.code.co_argcount]),
				defaults,
				'\n'.join('\t%s' % line for line in outer)
			)
	
	def execute(self, pc, block, stack, scope):
		if pc in self.hit:
			return -1
		self.hit.append(pc)
		
		opcd = ord(self.co_code[pc])
		name = opcode.opname[opcd]
		pc += 1
		
		args = [self, block, stack, scope]
		
		if opcd >= opcode.HAVE_ARGUMENT:
			arg, = struct.unpack('h', self.co_code[pc:pc+2])
			pc += 2
		
		if opcd in opcode.hasconst:
			args.append(self.code.co_consts[arg])
		elif opcd in opcode.haslocal:
			args.append(self.code.co_varnames[arg])
		elif opcd in opcode.hasname:
			args.append(self.code.co_names[arg])
		elif opcd in opcode.hasjrel:
			args.append(pc)
			args.append(arg)
		elif opcd >= opcode.HAVE_ARGUMENT:
			args.append(arg)
		
		if name.startswith('INPLACE_'): # Why is this separate?  Just an optimization in the Py core?
			name = 'BINARY_' + name[len('INPLACE_'):]
		if name in self.opcdmap:
			npc = self.opcdmap[name](*args)
			if npc != None:
				pc = npc
		elif name in self.binaryOpers:
			args.append(self.binaryOpers[name])
			self.binaryOp(*args[1:])
		else:
			raise Exception('Unknown opcode `%s\'' % name)
		
		return pc
	
	def opcode(func, opcdmap={}):
		opcdmap[func.__name__] = func
		return func
	
	@opcode
	def DUP_TOP(self, _block, stack, _scope):
		stack.append(stack[-1])
	@opcode
	def DUP_TOPX(self, _block, stack, _scope, count):
		stack += stack[-count:]
	
	@opcode
	def POP_TOP(self, block, stack, _scope):
		top = stack.pop()
		
		if isinstance(top, tuple) and len(top) == 2:
			use, top = top
		else:
			use = True
		
		if use:
			block.append('%s;' % top)
	@opcode
	def ROT_TWO(self, _block, stack, _scope):
		a, b = stack.pop(), stack.pop()
		stack.append(a)
		stack.append(b)
	@opcode
	def ROT_THREE(self, _block, stack, _scope):
		a, b, c = stack.pop(), stack.pop(), stack.pop()
		stack.append(a)
		stack.append(c)
		stack.append(b)
	
	@opcode
	def LOAD_ATTR(self, _block, stack, _scope, name):
		if name == 'new':
			stack.append('new %s' % stack.pop())
		else:
			stack.append('%s.%s' % (stack.pop(), name))
	@opcode
	def STORE_ATTR(self, block, stack, _scope, name):
		block.append('%s.%s = %s;' % (stack.pop(), name, stack.pop()))
	
	@opcode
	def LOAD_CONST(self, _block, stack, _scope, const):
		if const == None:
			stack.append('null')
		elif const is False:
			stack.append('false')
		elif const is True:
			stack.append('true')
		else:
			stack.append(repr(const))
	
	@opcode
	def LOAD_GLOBAL(self, _block, stack, _scope, name):
		if name == 'True':
			stack.append('true')
		elif name == 'False':
			stack.append('false')
		elif name == 'None':
			stack.append('null')
		else:
			stack.append(name)
	@opcode
	def STORE_GLOBAL(self, block, stack, scope, var):
		if stack[-1] == 'for':
			block.append(var)
			stack.pop()
		else:
			block.append('%s = %s;' % (var, stack.pop()))
	
	@opcode
	def LOAD_FAST(self, _block, stack, _scope, var):
		if var == 'self':
			var = 'this'
		stack.append(var)
	@opcode
	def STORE_FAST(self, block, stack, scope, var):
		if var in scope:
			decl = ''
		else:
			decl = 'var '
			scope.append(var)
		
		if stack[-1] == 'for':
			block.append(var)
			stack.pop()
		else:
			block.append('%s%s = %s;' % (decl, var, stack.pop()))
	
	@opcode
	def STORE_SUBSCR(self, block, stack, _scope):
		index, base, value = stack.pop(), stack.pop(), stack.pop()
		if isinstance(base, list) or isinstance(base, dict):
			base[index] = value
		else:
			block.append('(%s)[%s] = %s' % (base, index, value))
	
	@opcode
	def UNARY_NEGATIVE(self, _block, stack, _scope):
		stack.append('-(%s)' % stack.pop())
	@opcode
	def UNARY_NOT(self, _block, stack, _scope):
		stack.append('!(%s)' % stack.pop())
	
	@opcode
	def BINARY_SUBSCR(self, _block, stack, _scope):
		a, b = stack.pop(), stack.pop()
		stack.append('(%s)[%s]' % (b, a))
	
	@opcode
	def BINARY_POWER(self, _block, stack, _scope):
		a, b = stack.pop(), stack.pop()
		stack.append('Math.pow(%s, %s)' % (b, a))
	def binaryOp(self, _block, stack, _scope, oper):
		a, b = stack.pop(), stack.pop()
		stack.append('(%s) %s (%s)' % (b, oper, a))
	binaryOpers = dict(
		BINARY_ADD='+',
		BINARY_SUBTRACT='-',
		BINARY_MULTIPLY='*',
		BINARY_DIVIDE='/',
		BINARY_MODULO='%',
		BINARY_LSHIFT='<<',
		BINARY_RSHIFT='>>',
		BINARY_AND='&',
		BINARY_OR='|',
		BINARY_XOR='^'
	)
	
	@opcode
	def BUILD_MAP(self, _block, stack, _scope, _arg):
		stack.append(JsDict())
	
	@opcode
	def BUILD_LIST(self, _block, stack, _scope, count):
		stack.append(JsList([stack.pop() for i in xrange(count)][::-1]))
	
	@opcode
	def CALL_FUNCTION(self, _block, stack, _scope, count):
		if count == 0:
			stack.append(JsFunc(stack.pop()))
		else:
			stack.append(JsFunc(stack[-count-1], [str(elem) for elem in stack[-count:]]))
			del stack[-count-2:-1]
	
	@opcode
	def RETURN_VALUE(self, block, stack, _scope):
		val = stack.pop()
		if val != 'null':
			block.append('return %s;' % val)
		else:
			block.append('return;')
	
	@opcode
	def COMPARE_OP(self, _block, stack, _scope, opname):
		a, b = stack.pop(), stack.pop()
		stack.append('%s %s %s' % (b, opcode.cmp_op[opname], a))
	
	@opcode
	def GET_ITER(self, _block, stack, _scope):
		pass
	@opcode
	def FOR_ITER(self, block, stack, _scope, pc, delta):
		block.append(stack.pop())
		stack[0] = 'for'
		stack.append('for')
	
	def addSemicolon(self, line):
		if (
			line.lstrip().startswith('if') or 
			line.lstrip().startswith('else') or 
			line.lstrip().startswith('while') or 
			line.lstrip().startswith('for') or 
			line.rstrip().endswith(';') or
			line.rstrip().endswith('}')
		):
			return ''
		
		return ';'
	@opcode
	def SETUP_LOOP(self, block, stack, scope, pc, delta):
		nblock = []
		nstack = ['while']
		nscope = [var for var in scope]
		tpc = pc
		while tpc != -1 and tpc < len(self.co_code):
			tpc = self.execute(tpc, block=nblock, stack=nstack, scope=nscope)
		
		if nstack[0] == 'while':
			try:
				while_, cond = nblock[0]
				assert while_ == 'while'
				
				block.append('while(%s)%s' % (cond, len(nblock) != 2 and ' {' or ''))
				for line in nblock[1:]:
					block.append('\t%s' % line)
				if len(nblock) != 2:
					block.append('}')
			except Exception:
				raise Exception('Could not build while block %i-%i, nblock follows: %r' % (pc, pc+delta, nblock))
		elif nstack[0] == 'for' and isinstance(nblock[0], JsFunc) and nblock[0].name == 'range':
			args = nblock[0].args
			var = nblock[1]
			if len(args) == 1:
				begin = '0'
				end = args[0]
				step = '1'
			elif len(args) == 2:
				begin, end = args
				step = '1'
			elif len(args) == 3:
				begin, end, step = args
			
			setup = ['%s = %s' % (var, begin)]
			
			if not end.isdigit():
				setup.append('__end%i = %s' % (self.varcount, end))
				end = '__end%i' % self.varcount
				self.varcount += 1
			
			if not step.isdigit():
				setup.append('__step%i = %s' % (self.varcount, step))
				step = '__step%i' % self.varcount
				self.varcount += 1
			
			expr = '%s; %s < %s; %s += %s' % (', '.join(setup), var, end, var, step)
			block.append('for(%s)%s' % (expr, len(nblock) != 3 and ' {' or ''))
			for line in nblock[2:]:
				block.append('\t%s%s' % (line, self.addSemicolon(line)))
			if len(nblock) != 3:
				block.append('}')
		elif nstack[0] == 'for':
			block.append('for(var %s in %s)%s' % (nblock[1], nblock[0], len(nblock) != 3 and ' {' or ''))
			for line in nblock[2:]:
				block.append('\t%s%s' % (line, self.addSemicolon(line)))
			if len(nblock) != 3:
				block.append('}')
		
		return pc + delta
	@opcode
	def BREAK_LOOP(self, block, _stack, _scope):
		block.append('break;')
	
	@opcode
	def JUMP_IF_FALSE(self, block, stack, scope, pc, delta):
		if len(stack) >= 2 and stack[-2] == 'while':
			block.append(('while', stack[-1]))
			stack.append((False, stack.pop()))
		else:
			cond = stack.pop()
			stack.append((False, cond))
			nblock = [('if', pc + delta)]
			nstack = [elem for elem in stack]
			nscope = [var for var in scope]
			tpc = pc
			while tpc != -1 and tpc < pc + delta and tpc < len(self.co_code):
				tpc = self.execute(tpc, block=nblock, stack=nstack, scope=nscope)
			
			block.append('if(%s)%s' % (cond, len(nblock) != 2 and ' {' or ''))
			hasElse = False
			for line in nblock:
				if isinstance(line, tuple):
					if line[0] == 'else':
						hasElse = True
						pc += delta
						delta = line[1] - pc
						break
					else:
						continue
				block.append('\t%s%s' % (line, self.addSemicolon(line)))
			if len(nblock) != 2:
				block.append('}')
			
			if hasElse:
				nblock = []
				nstack = [elem for elem in stack]
				nscope = [var for var in scope]
				tpc = pc
				while tpc != -1 and tpc < pc + delta and tpc < len(self.co_code):
					tpc = self.execute(tpc, block=nblock, stack=nstack, scope=nscope)
				if len(nblock) != 0:
					block.append('else%s' % (len(nblock) != 1 and ' {' or ''))
					for line in nblock:
						block.append('\t%s%s' % (line, self.addSemicolon(line)))
					if len(nblock) != 1:
						block.append('}')
			
			return pc + delta
	
	@opcode
	def JUMP_IF_TRUE(self, block, stack, scope, pc, delta):
		return self.JUMP_IF_FALSE(block, stack[:-1] + ['!(%s)' % stack[-1]], scope, pc, delta)
	
	@opcode
	def JUMP_FORWARD(self, block, _stack, _scope, pc, delta):
		if isinstance(block[0], tuple) and block[0][0] == 'if':
			del block[0]
			block.append(('else', pc + delta))
		return pc + delta
	
	@opcode
	def JUMP_ABSOLUTE(self, block, _stack, _scope, pc):
		if len(block) > 0 and isinstance(block[0], tuple) and block[0][0] == 'if':
			del block[0]
			block.append(('else', pc))
		return pc
	
	@opcode
	def STOP_CODE(self, _block, _stack, _scope):
		pass
	
	def __str__(self):
		return self.js

def pyvascript(context):
	context._push_buffer()
	context.caller_stack.nextcaller.body()
	code = context._pop_buffer().getvalue()
	lines = code.split(u'\n')
	
	imps = []
	top = []
	blocks = []
	i = 0
	while i < len(lines):
		start = i
		if lines[i].startswith(u'import') or lines[i].startswith(u'from'):
			imps.append(lines[i])
		elif lines[i].startswith(u'class') or lines[i].startswith(u'def'):
			i += 1
			while i < len(lines) and (lines[i] == u'' or lines[i][0] in u' \t'):
				i += 1
			i -= 1
			blocks.append([line for line in lines[start:i] if line.strip()])
		elif lines[i].strip():
			top.append(lines[i])
		i += 1
	
	code = [imp for imp in imps]
	names = []
	if len(top):
		names.append('__top__')
		code += [u'@JavaScript', 'def __top__():'] + ['\t'+line for line in top]
	
	for block in blocks:
		first = block[0].strip()
		
		if first.startswith(u'class'):
			block[0] = block[0].rstrip()[:-1]
			if block[0][-1] == u')':
				block[0] = block[0][:-1] + u', JavaScript):'
			else:
				block[0] += u'(JavaScript):'
		elif first.startswith(u'def'):
			block = [u'@JavaScript'] + block
		else:
			first = block[1].strip()
		
		name = first.split(u' ', 1)[1].split(u'(', 1)[0].split(u':', 1)[0]
		if first.startswith(u'class'):
			block.append(u'%s = %s()' % (name, name))
		names.append(name)
		code += block
	
	code = u'\n'.join(code)
	#file('foo.py', 'w').write(code)
	
	code = compiler.compile(code, '<pyvascript>', 'exec')
	globs = dict(JavaScript=JavaScript)
	eval(code, globs)
	
	for imp in imps:
		module = imp.split(u' ', 2)[1]
		module = __import__(module, globals(), locals(), ['__js_deps__'], -1)
		for jsDep in getattr(module, '__js_deps__', ()):
			context.write(u'<script src="%s" language="JavaScript"></script>\n' % jsDep)
	
	context.write(u'<script language="JavaScript">\n%s</script>' % '\n'.join(unicode(globs[name]) for name in names))
