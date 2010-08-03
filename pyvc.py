import sys
from Javascript import compileString

def main(*args):
	minify = True
	if args[0] == '--no-minify':
		minify = False
		args = args[1:]
	outfn = None
	if len(args) == 1:
		infn = args[0]
	else:
		infn, outfn = args
	
	code = file(infn, 'r').read()
	if outfn == None:
		outfp = sys.stdout
	else:
		outfp = file(outfn, 'w')
	outfp.write(compileString(code, minify=minify))

def usage(fn):
	print 'Usage: %s [--no-minify] <in-file.py> [out-file.js]' % fn

if __name__=='__main__':
	if len(sys.argv) < 2:
		usage(sys.argv[0])
	else:
		main(*sys.argv[1:])
