import os
import sys
import re

PARSE_FILE = 0
EXTERNAL_FILE = 1
ALREADY_SCANNED = 2

CPP_SRC_FILE_EXT = set([ ".cpp" ,  ".c" ,  ".cxx", ".cc"])
CPP_HEADER_FILE_EXT = set([".hpp" , ".h" , ".hxx" , ".hh" , ".inl"])

INCLUDE_FILE_MATCHER = re.compile(r'#include\s*[<\"]([\w.\\/]*)[>\"]')
UP_DIRECTORY_MATCHER = re.compile(r'(..[\\/])')

def IsCppHeaderFile(ext):
	return  ext in CPP_HEADER_FILE_EXT
	
def IsCppSourceFile(ext):
	return ext in CPP_SRC_FILE_EXT

def IsCppFile(ext):
	return IsCppHeaderFile(ext) or IsCppSourceFile(ext)
	
def AdjustFileExtension(ext):
	if ext[0] != '.':
		ext = '.' + ext
	

class SourceInfo:
	def __init__(self, baseDir , outputDir, outputName):
		self.m_scannedFiles = set()
		
		self.m_baseDir = baseDir; 
		self.m_outputDir = outputDir
		
		self.m_sourceAmalgamation = None
		self.m_headerAmalgamation = None
		
		self.m_outputName = outputName
		self.m_sourceFileExt = ".cpp"
		self.m_headerFileExt = ".hpp"
		
	def InitAmalgamationStreams(self):
		headerName = self.m_outputName + self.m_headerFileExt
		headerPath = os.path.join(self.m_outputDir , headerName)
		sourcePath = os.path.join(self.m_outputDir , self.m_outputName + self.m_sourceFileExt)
		
		self.m_headerAmalgamation = open (headerPath , 'w')
		self.m_sourceAmalgamation = open (sourcePath , 'w')
		
		self.m_sourceAmalgamation.write('#include"%s"\n' % (headerName))
		
		print "creating source Amalgamation:" + sourcePath
		print "creating source Amalgamation:" + headerPath
		
	def CloseAmalgamationStreams(self):
		self.m_headerAmalgamation.close()
		self.m_sourceAmalgamation.close()
		
	def GetOutputStreamForExt(self , ext):
		if IsCppSourceFile(ext):
			return self.m_sourceAmalgamation
			
		elif IsCppHeaderFile(ext):
			return self.m_headerAmalgamation
			
		return None
				
	def SetSourceFileExt(ext):
		AdjustFileExtension(ext)
		
		if not IsCppSourceFile(ext):
			print "Warning: %s is not a recognized c++ source file extension" % (ext)
		
		self.m_sourceFileExt = ext
		
	def SetHeaderFileExt(ext):
		AdjustFileExtension(ext)
		
		if not IsCppHeaderFile(ext):
			print "Warning: %s is not a recognized c++ header file extension" % (ext)
		
		self.m_sourceFileExt = ext
	
	def PrintParseFileMessage(self , message , path  , depth):
		tabs = ''
		for i in range(depth):
			tabs = tabs + '\t'
		
		print "%s%s: %s" % (tabs , message ,  path)
		
	def GetAdjustedPath(self , pwd , include , dirCount):
		dirs = pwd.split('/')
		for i in range(dirCount):
			dirs.pop()
		
		adjustedPwd = "/".join(dirs)
		adjustedName = include.replace("../" , "")
		absolutePath = os.path.join(adjustedPwd , adjustedName)
		
		if os.path.isfile(absolutePath):
			return absolutePath
			
		return include
		
	def GetAbsoluteSourcePath(self, pwd, include):
		if os.path.isabs(include):
			return include
		
		#handle "../" in include string
		result = UP_DIRECTORY_MATCHER.findall(include)
		if result:
			return self.GetAdjustedPath(pwd, include, len(result))
			
		
		# check for file in pwd, if this doesnt exist assume included from base source dir
		absolutePath = os.path.join(pwd , include)
		if os.path.isfile(absolutePath):
			return absolutePath
		
		absolutePath = os.path.join(self.m_baseDir , include)
		if os.path.isfile(absolutePath):
			return absolutePath
		
		return include
		
	def ShouldParseFile(self , path , ext):
		if (path in self.m_scannedFiles): return ALREADY_SCANNED
		
		#todo: make sure that path is within the include directory....
		if not IsCppFile(ext) or not os.path.exists(path): 
			print "external file- path:%s\text:%s" % (path, ext)
			return EXTERNAL_FILE
		
		return PARSE_FILE
		
	def ScanSourceFile(self, path , depth):
		dirpath , filename = os.path.split(path)
		ext = os.path.splitext(filename)[1]

		
		info = self.ShouldParseFile(path, ext)
		if info != PARSE_FILE:
			#self.PrintParseFileMessage("Skipping" , path , depth)
			return info
		
		self.m_scannedFiles.add(path)
		
		#self.PrintParseFileMessage("Scanning" , path , depth)
		stream = self.GetOutputStreamForExt(ext)
		
		src= open (path , 'r')
		lines = src.readlines()
		
		for line in lines:
			result = INCLUDE_FILE_MATCHER.findall(line)
			
			#if no include file found copy the line to the amalgamation, otherwise parse the include file
			if result:
				includeFile = self.GetAbsoluteSourcePath(dirpath, result[0])
				#self.PrintParseFileMessage("include file found" , includeFile , depth+1)
				call = self.ScanSourceFile(includeFile , depth + 1)
				
				#only include external files once
				if call == EXTERNAL_FILE:
					self.m_scannedFiles.add(includeFile)
					stream.write(line)
			else:
				stream.write(line)
		
		src.close()
		src = None
		
		return info
		
		
		
	def ParseSourceDirectory(self):
		
		self.InitAmalgamationStreams()
		
		for root, subFolders, files in os.walk(self.m_baseDir):
			for filename in files:
				path =  os.path.join(root, filename)
				#self.PrintParseFileMessage("Walk" , path , 0)
				self.ScanSourceFile(path , 0)
				
		self.CloseAmalgamationStreams()
	
			
			
baseDir = sys.argv[1]
outputPath = sys.argv[2]
outputName = sys.argv[3]

print "base dir: " + baseDir
print "output dir: " + outputPath
print "output name: " + outputName

sourceInfo = SourceInfo(baseDir , outputPath, outputName)

sourceInfo.ParseSourceDirectory()