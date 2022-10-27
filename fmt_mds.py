from inc_noesis import *
import io
from collections import defaultdict

bDarkCloud1 = False

def registerNoesisTypes():
	handle = noesis.register("Dark Cloud",".mds")
	noesis.setHandlerTypeCheck(handle, CheckType)
	noesis.setHandlerLoadModel(handle, LoadMDS)
	handle = noesis.register("Dark Cloud",".chr;")
	noesis.setHandlerTypeCheck(handle, CheckType)
	noesis.setHandlerLoadModel(handle, LoadCHR)
	handle = noesis.register("Dark Cloud",".img")
	noesis.setHandlerTypeCheck(handle, CheckType)
	noesis.setHandlerLoadRGBA(handle, LoadIMG)
	return 1

def parseMotionKeys(lines,i):
	j = 1
	keys = []
	while lines[i+j].split()[0] != "KEY_END;":
		line = lines[i+j][:-2].split(",")
		keys.append([float(a) for a in line[1:]])
		j+=1
	return keys

def parseContainer(bs,offset=0):
	bs.seek(offset)
	sectionInfo = {} # name -> [magic, offset, size]
	size = 1
	offset = 1
	while size > 0 or offset > 0:
		checkpoint = bs.tell()
		name = bs.readString()
		bs.seek(checkpoint + 68)
		size = bs.readInt()
		offset = bs.readInt()
		if size > 0 or offset > 0:
			bs.readBytes(4)
			magic = bs.readUInt()
			sectionInfo[name] = [magic,bs.tell()-4,size]
			bs.seek(checkpoint+offset)
	return sectionInfo	
	
def LoadIMG(data, texList):
	LoadTexture(data, texList)
	return 1

def LoadMDS(data, mdlList):
	LoadOldModel(data, mdlList, [], [], [], [], [])
	return 1

def LoadCHR(data, mdlList):

	ctx = rapi.rpgCreateContext()
	bs = NoeBitStream(data)
	bs.setEndian(NOE_LITTLEENDIAN)
	
	bMDSFound = False
	mdsOffset = 0
	imgOffset = 0
	motionData = []
	bbpData = []
	wgtData = []
	textureList = []
	animList = []
	keys = []
	cfgName = "info.cfg"
	bCFGFound = False
	
	chrInfo = parseContainer(bs,0)
	# for k in chrInfo:
		# print(k)
	
	if not "info.cfg" in chrInfo:
		print("info.cfg not found")
		for k in chrInfo:
			if len(k)>4 and k[-4:] == ".cfg":
				bCFGFound = True
				cfgName = k
	else:
		bCFGFound = True

	if not bCFGFound:
		print("cfg not found")
		return 1
	
	#info parsing
	magic, offset, size = chrInfo[cfgName]
	
	fh_bytes = io.BytesIO(data[offset:offset+size])
	f = io.TextIOWrapper(fh_bytes, encoding='utf-8', errors='replace')
	lines = f.readlines()
	
	imgName = modelName = None
	motionNames = []
	bbpNames = []
	wgtNames = []
	
	for i,line in enumerate(lines):
		if len(line.split()) == 0:
			continue		
		
		if line.split()[0] == "IMG":
			if bDarkCloud1:
				imgName = line.split()[1][2:][1:-1].lower()
			else:
				imgName = line.split()[2][:-1][1:-1].lower()			
		elif line.split()[0] == "MODEL":
			if bDarkCloud1:
				modelName = line.split()[1][1:-1].lower()
			else:
				modelName = line.split()[1][:-1][1:-1].lower()
			
		elif line.split()[0] == "MOTION":
			motionNames.append(line.split()[2][:-1][1:-1])
			if len(line.split()) > 2:
				bbpNames.append(line.split()[3][:-1][1:-1])
				wgtNames.append(line.split()[4][:-1][1:-1])
		elif line.split()[0] == "KEY_START;":
			keys = parseMotionKeys(lines,i)
	if imgName in chrInfo:
		magic, offset, size = chrInfo[imgName]
		bs.seek(offset)
		LoadTexture(bs, textureList,size,True)
	else:
		print(chrInfo)
		print(imgName)
	if modelName in chrInfo:
		magic, offset, size = chrInfo[modelName]
		bs.seek(offset)
		for motionName in motionNames:
			if motionName in chrInfo:
				magic, offset, size = chrInfo[motionName]
				motionData.append(data[offset:offset+size])
		for bbpName in bbpNames:
			if bbpName in chrInfo:
				magic, offset, size = chrInfo[bbpName]
				bbpData.append(data[offset:offset+size])
		for wgtName in wgtNames:
			if wgtName in chrInfo:
				magic, offset, size = chrInfo[wgtName]
				wgtData.append(data[offset:offset+size])
		LoadOldModel(bs,mdlList,textureList, animList, motionData, bbpData, wgtData, bIsBS=True,keys=keys)
	else:
		print("no model file")
	return 1
	
def Align(bs, n):
	value = bs.tell() % n
	if (value):
		bs.seek(n - value, 1)
	
def CheckType(data):
	return 1

def LoadTexture(data, textureList, size,bIsBS = False):

	if not bIsBS:
		bs = NoeBitStream(data)
	else:
		bs = data
		
	names = []
	offsets = []
	sizes = []
	
	baseOffset = bs.tell()
	bs.setEndian(NOE_LITTLEENDIAN)
	rapi.processCommands("-texnorepfn")
	magic = bs.readUInt()
	if magic == 4672841 or magic == 3296585:
		texCount = bs.readUInt()
		bs.readBytes(8)
		for i in range(texCount):
			checkpoint = bs.tell()
			names.append(bs.readString())
			bs.seek(checkpoint+32)
			offsets.append(bs.readUInt())
			bs.readBytes(12)
		offsets.append(size)
		for i in range(texCount):
			if names[i] == "#texanime":
				continue
			bs.seek(offsets[i]+4+baseOffset)
			
			a = 0
			checkpoint = bs.tell()
			bs.seek(12,1)
			if bs.readUByte() == 112:
				a = noePack("<I",843925844) #TM2
			else:
				a = noePack("<I",860703060) #TM3
			bs.seek(checkpoint)
			b = rapi.loadTexByHandler(a + bs.readBytes(offsets[i+1]-offsets[i]-4),".tm2")
			b.name = names[i]+".dds"
			textureList.append(b)
	else:
		bs.readBytes(4)
		texCount = bs.readUInt()
		bs.readBytes(4)
		for i in range(texCount):
			checkpoint = bs.tell()
			names.append(bs.readString())
			bs.seek(checkpoint+36)
			offsets.append(bs.readUInt())
			bs.readBytes(12)
			sizes.append(bs.readUInt()-4)
			bs.readBytes(8)
		for i in range(texCount):
			if names[i] == "#texanime":
				continue
			bs.seek(offsets[i]+4+baseOffset)
			
			a = 0
			checkpoint = bs.tell()
			bs.seek(12,1)
			if bs.readUByte() == 112:
				a = noePack("<I",843925844) #TM2
			else:
				a = noePack("<I",860703060) #TM3
			bs.seek(checkpoint)
			b = rapi.loadTexByHandler(a + bs.readBytes(sizes[i]),".tm2")
			b.name = names[i]+".dds"
			textureList.append(b)

def processOldTrack(bs, width, timingCount, framerate=30, keys=[]):
	
	frameToKFV = {}
	keyframedValues = []
	if keys:
		for _ in range(timingCount):
			timing = bs.readUInt()
			bs.readBytes(12)
			vector = bs.read('<' + str(width) + 'f')
			if width == 3:
				bs.readUInt()
			if width == 4:
				frameToKFV[timing] = NoeKeyFramedValue(timing/framerate,NoeQuat([vector[1],vector[2],vector[3],vector[0]]))
			else:
				frameToKFV[timing] = NoeKeyFramedValue(timing/framerate,NoeVec3([vector[0],vector[1],vector[2]]))
		
		return frameToKFV
	else:
		for _ in range(timingCount):
			timing = bs.readUInt()
			bs.readBytes(12)
			vector = bs.read('<' + str(width) + 'f')
			if width == 3:
				bs.readUInt()
			if width == 4:
				keyframedValues.append(NoeKeyFramedValue(timing/framerate,NoeQuat([vector[1],vector[2],vector[3],vector[0]])))
			else:
				keyframedValues.append(NoeKeyFramedValue(timing/framerate,NoeVec3([vector[0],vector[1],vector[2]])))
		
		return keyframedValues

def LoadOldMotion(data, jointList, animList, framerate=30,keys=[]):
	bs = NoeBitStream(data)
	bs.setEndian(NOE_LITTLEENDIAN)
	boneToRotKFVs = {}
	boneToPosKFVs = {}
	boneToScaleKFVs = {}
	knownSemantics = [0,1,2]
	keyFramedBoneList = []
	
	if keys:
		boneToRotFrameMap = {}
		boneToPosFrameMap = {}
		boneToScaleFrameMap = {}
		blockSize = 1
		while blockSize:
			start = bs.tell()
			boneID = bs.readUInt()
			bs.readUInt()
			semantic = bs.readUInt()
			# if semantic not in knownSemantics:
				# print(semantic)
			# assert(semantic in knownSemantics)
			headerSize = bs.readUInt()
			timingCount = bs.readUInt()
			blockSize = bs.readUInt()
			bs.readBytes(8)
			
			bs.seek(start + headerSize)
			
			if boneID not in boneToRotFrameMap:
				boneToRotFrameMap[boneID] = {}
				boneToPosFrameMap[boneID] = {}
				boneToScaleFrameMap[boneID] = {}
			
			if semantic == 0: #rotation
				boneToRotFrameMap[boneID] = processOldTrack(bs, 4, timingCount, framerate, keys)
			elif semantic == 1: #scale
				boneToScaleFrameMap[boneID] = processOldTrack(bs, 3, timingCount, framerate, keys)
			elif semantic == 2: #position
				boneToPosFrameMap[boneID] = processOldTrack(bs, 3, timingCount, framerate, keys)
			bs.seek(start + blockSize)
			
			
		for i,key in enumerate(keys): #for all anims
			keyFramedBoneList = []
			for boneID in boneToRotFrameMap:
				rotNoeKeyFramedValues = []
				posNoeKeyFramedValues = []
				scaleNoeKeyFramedValues = []
				for timing in range(int(key[0]),int(key[1])+1):
					if boneToRotFrameMap[boneID] and timing in boneToRotFrameMap[boneID]:
						rotNoeKeyFramedValues.append(boneToRotFrameMap[boneID][timing])
					if boneToPosFrameMap[boneID] and timing in boneToPosFrameMap[boneID]:
						posNoeKeyFramedValues.append(boneToPosFrameMap[boneID][timing])
					if boneToScaleFrameMap[boneID] and timing in boneToScaleFrameMap[boneID]:
						scaleNoeKeyFramedValues.append(boneToScaleFrameMap[boneID][timing])
		
				actionBone = NoeKeyFramedBone(boneID)
				if (len(rotNoeKeyFramedValues) > 0):
					actionBone.setRotation(rotNoeKeyFramedValues, noesis.NOEKF_ROTATION_QUATERNION_4)
				if (len(posNoeKeyFramedValues) > 0):
					actionBone.setTranslation(posNoeKeyFramedValues, noesis.NOEKF_TRANSLATION_VECTOR_3)
				if (len(scaleNoeKeyFramedValues) > 0):
					actionBone.setScale(scaleNoeKeyFramedValues, noesis.NOEKF_SCALE_VECTOR_3)
				keyFramedBoneList.append(actionBone)
			
			anim = NoeKeyFramedAnim('anim_' + str(i), jointList, keyFramedBoneList, framerate*key[2])
			animList.append(anim)
	else:
		boneToRotFrameMap = {}
		boneToPosFrameMap = {}
		boneToScaleFrameMap = {}
		blockSize = 1
		while blockSize:
			start = bs.tell()
			boneID = bs.readUInt()
			bs.readUInt()
			semantic = bs.readUInt()
			# if semantic not in knownSemantics:
				# print(semantic)
			# assert(semantic in knownSemantics)
			headerSize = bs.readUInt()
			timingCount = bs.readUInt()
			blockSize = bs.readUInt()
			bs.readBytes(8)
			
			bs.seek(start + headerSize)
			
			if boneID not in boneToRotFrameMap:
				boneToRotFrameMap[boneID] = {}
				boneToPosFrameMap[boneID] = {}
				boneToScaleFrameMap[boneID] = {}
			
			if semantic == 0: #rotation
				boneToRotFrameMap[boneID] = processOldTrack(bs, 4, timingCount, framerate, keys)
			elif semantic == 1: #scale
				boneToScaleFrameMap[boneID] = processOldTrack(bs, 3, timingCount, framerate, keys)
			elif semantic == 2: #position
				boneToPosFrameMap[boneID] = processOldTrack(bs, 3, timingCount, framerate, keys)
			bs.seek(start + blockSize)
			
			for boneID in boneToRotFrameMap:
				rotNoeKeyFramedValues = []
				posNoeKeyFramedValues = []
				scaleNoeKeyFramedValues = []
				if boneToRotFrameMap[boneID]:
					rotNoeKeyFramedValues = boneToRotFrameMap[boneID]
				if boneToPosFrameMap[boneID]:
					posNoeKeyFramedValues = boneToPosFrameMap[boneID]
				if boneToScaleFrameMap[boneID]:
					scaleNoeKeyFramedValues = boneToScaleFrameMap[boneID]
		
				actionBone = NoeKeyFramedBone(boneID)
				if (len(rotNoeKeyFramedValues) > 0):
					actionBone.setRotation(rotNoeKeyFramedValues, noesis.NOEKF_ROTATION_QUATERNION_4)
				if (len(posNoeKeyFramedValues) > 0):
					actionBone.setTranslation(posNoeKeyFramedValues, noesis.NOEKF_TRANSLATION_VECTOR_3)
				if (len(scaleNoeKeyFramedValues) > 0):
					actionBone.setScale(scaleNoeKeyFramedValues, noesis.NOEKF_SCALE_VECTOR_3)
				keyFramedBoneList.append(actionBone)
			
		anim = NoeKeyFramedAnim('anim', jointList, keyFramedBoneList, framerate)
		animList.append(anim)
	
def LoadOldModel(data, mdlList,textureList, animList, motionData, bbpData, wgtData, modeltransform = NoeMat43(), bCreateContext=True, baseName="", bIsBS=False, keys=[]):
	framerate = 30
	
	#dumb hack
	# if not textureList:
		# LoadTexture(rapi.loadPairedFileOptional("img file", ".img"), textureList)
		
	if bCreateContext:
		ctx = rapi.rpgCreateContext()
	if not bIsBS:
		bs = NoeBitStream(data)
	else:
		bs = data
	baseOffset = bs.tell()
	bs.setEndian(NOE_LITTLEENDIAN)
	
	if len(bbpData):
		assert(len(bbpData) == 1)
		bbpBs = NoeBitStream(bbpData[0])
	# else:
		# bbpData.append(rapi.loadPairedFileOptional("bbp file", ".bbp"))
		# bbpBs = NoeBitStream(bbpData[0])
		
	if len(wgtData):
		assert(len(wgtData) == 1)
		wgtBs = NoeBitStream(wgtData[0])
	# else:
		# wgtData.append(rapi.loadPairedFileOptional("wgt file", ".wgt"))
		# wgtBs = NoeBitStream(wgtData[0])
		
	
	#header
	bs.readBytes(8)
	jointCount = bs.readUInt()
	dataOffset = bs.readUInt()
	
	#joints
	jointList = []
	jointMDTOffsetList = []
	matList = []
	boneIndexToMesh = {}
	boneIndexToSkinningInfo = {}
	meshToBoneIndex = {}
	meshToVertMap = {} #mesh Index -> vertex map
	
	bs.seek(dataOffset+baseOffset)
	for i in range(jointCount):
		start = bs.tell()
		index = bs.readUInt()
		blockSize = bs.readUInt()
		name = bs.readString()
		bs.seek(start + 40)
		mdtOffset = bs.readUInt()
		if mdtOffset:
			jointMDTOffsetList.append(mdtOffset)
			matList.append(i)
			boneIndexToMesh[i] = len(matList)-1
			meshToBoneIndex[len(matList)-1] = i
		parent = bs.readInt()
		if len(bbpData) and not bDarkCloud1:
			mat = NoeMat44.fromBytes(bbpBs.readBytes(64)).toMat43()
		else:
			mat = NoeMat44.fromBytes(bs.readBytes(64)).toMat43()
		joint = NoeBone(index, name, mat, None, parent)
		jointList.append(joint)
		bs.seek(start + blockSize)
	assert(sorted(jointMDTOffsetList) == jointMDTOffsetList)
	if not len(bbpData):
		jointList = rapi.multiplyBones(jointList)
	
	submeshCount = len(matList)
	
	#parse weights if relevant
	if jointList and len(wgtData):
		while(wgtBs.tell() < wgtBs.getSize()):
			meshIndex = boneIndexToMesh[wgtBs.readUInt()]
			if meshIndex not in meshToVertMap:
				meshToVertMap[meshIndex] = defaultdict(list)
			boneID = wgtBs.readUInt()
			wgtBs.readBytes(8)
			vertexCount = wgtBs.readUInt()
			blockSize = wgtBs.readUInt()
			wgtBs.readBytes(8)
			for _ in range(vertexCount):
				vertexIndex = wgtBs.readUInt()
				wgtBs.readBytes(12)
				weight = wgtBs.readFloat()
				wgtBs.readBytes(12)
				meshToVertMap[meshIndex][vertexIndex].append([boneID, weight/100])
	# for k in meshToVertMap:
		# print(meshToVertMap[k])
	# if not len(motionData) and jointList:
		# motionData.append(rapi.loadPairedFileOptional("motion file", ".mot"))
	if len(motionData) and jointList:
		for a in motionData:
			LoadOldMotion(a,jointList, animList,30, keys)
	
	materialList = {}
	for i in range(submeshCount):
		textureNameList = []
		start = bs.tell()
		bs.readBytes(8) #magic + header length
		blockSize = bs.readUInt()
		
		pCount = bs.readUInt()
		pOffset = bs.readUInt()
		nCount = bs.readUInt()
		nOffset = bs.readUInt()
		bs.readBytes(8)
		indexSize = bs.readUInt()
		indexOffset = bs.readUInt()
		uvCount = bs.readUInt()
		uvOffset = bs.readUInt()
		materialInfoCount = bs.readUInt()
		materialInfoOffset = bs.readUInt()	

		# positions
		bs.seek(start + pOffset)
		pValues = []
		for _ in range(pCount):
			pValues += bs.read('<3f')
			bs.readFloat()
		
		# normals
		bs.seek(start + nOffset)
		nValues = []
		for _ in range(nCount):
			nValues += bs.read('<3f')
			bs.readFloat()
		
		# uvOffset
		bs.seek(start + uvOffset)
		uvValues = []
		for _ in range(uvCount):
			uvValues += bs.read('<2f')
			bs.read('<2f')
			
		#skinning
		if i in meshToVertMap:
			bwValues = []
			biValues = []
			for u in range(pCount):
				if u in meshToVertMap[i]:
					for v in range(len(meshToVertMap[i][u])):
						biValues.append(meshToVertMap[i][u][v][0])
						bwValues.append(meshToVertMap[i][u][v][1])
					for v in range(4-len(meshToVertMap[i][u])):
						biValues.append(0)
						bwValues.append(0)
				else:
					biValues.append(matList[i])
					bwValues.append(1)
					for _ in range(3):
						biValues.append(0)
						bwValues.append(0)
		else:
			bwValues = []
			biValues = []
			for _ in range(pCount):				
				biValues.append(matList[i])
				bwValues.append(1)
				for _ in range(3):
					biValues.append(0)
					bwValues.append(0)
			
		# material 
		bs.seek(start + materialInfoOffset)
		for _ in range(materialInfoCount):
			checkpoint = bs.tell()
			bs.seek(52,1)
			name = bs.readString()
			if name not in materialList:
				materialList[name] = name
			textureNameList.append(name)
			bs.seek(checkpoint+96)
		# indices 
		bs.seek(start + indexOffset)
		bs.readBytes(8)
		secondCount = bs.readUInt()
		bs.readUInt()
		for u in range(secondCount):
			type = bs.readUShort()
			width = 4 if bs.readUShort() else 3
			idxCount = bs.readUInt()
			textureIndex = bs.readUInt()
		
			vertexToIndex = {}
			posIdxList = {}
			idxBuffer = []
			maxIdx = pCount
			idxBuffer = []
			for _ in range(idxCount):
				posIdx = bs.readUInt()
				normIdx = bs.readUInt()
				uvIdx = bs.readUInt()
				if width == 4:
					bs.readUInt()
				
				vertex = (posIdx, normIdx, uvIdx)
				if vertex in vertexToIndex:
					idxBuffer.append(vertexToIndex[vertex])
				else:
					if posIdx in posIdxList:
						vertexToIndex[vertex] = maxIdx
						idxBuffer.append(maxIdx)
						maxIdx+=1				
					else:
						posIdxList[posIdx] = True
						vertexToIndex[vertex] = posIdx
						idxBuffer.append(posIdx)
			finalIdxBuffer = bytes()
			for idx in idxBuffer:
				finalIdxBuffer+=noePack('H', idx)
			
			vertexBufferValues = [[] for a in range(maxIdx)]
			for vertex, index in vertexToIndex.items():
				for j in range(3):
					vertexBufferValues[index].append(pValues[vertex[0]*3+j])
				for j in range(3):
					vertexBufferValues[index].append(nValues[vertex[1]*3+j])
				for j in range(2):
					vertexBufferValues[index].append(uvValues[vertex[2]*2+j])
				if jointList:
					for j in range(4):
						vertexBufferValues[index].append(biValues[vertex[0]*4+j])
					for j in range(4):
						vertexBufferValues[index].append(bwValues[vertex[0]*4+j])
					
			vertexBuffer = bytes()		
			for vertex in vertexBufferValues:
				if len(vertex):
					for j in range(3):
						vertexBuffer += noePack('f',vertex[j])
					for j in range(3):
						vertexBuffer += noePack('f',vertex[j+3])
					for j in range(2):
						vertexBuffer += noePack('f',vertex[j+6])
					if jointList:
						for j in range(4):
							vertexBuffer += noePack('h',vertex[j+8])
						for j in range(4):
							vertexBuffer += noePack('f',vertex[j+8+4])
				else:
					for j in range(3):
						vertexBuffer += noePack('f',0)
					for j in range(3):
						vertexBuffer += noePack('f',0)
					for j in range(2):
						vertexBuffer += noePack('f',0)
					if jointList:
						for j in range(4):
							vertexBuffer += noePack('h',0)
						for j in range(4):
							vertexBuffer += noePack('f',0)
			
			vStride = 32 + 6 * ( 4 if jointList else 0)
			rapi.rpgBindPositionBufferOfs(vertexBuffer, noesis.RPGEODATA_FLOAT, vStride,0)
			rapi.rpgBindNormalBufferOfs(vertexBuffer, noesis.RPGEODATA_FLOAT, vStride,12)
			rapi.rpgBindUV1BufferOfs(vertexBuffer,noesis.RPGEODATA_FLOAT,vStride,24)
			if jointList:
				rapi.rpgBindBoneIndexBufferOfs(vertexBuffer, noesis.RPGEODATA_SHORT,vStride,32, 4)
				rapi.rpgBindBoneWeightBufferOfs(vertexBuffer, noesis.RPGEODATA_FLOAT, vStride,40, 4)				
			rapi.rpgSetTransform(jointList[matList[i]].getMatrix())
			# rapi.rpgSetName(str(i))
			rapi.rpgSetMaterial(textureNameList[textureIndex])
					
			if type == 4:
				rapi.rpgCommitTriangles(finalIdxBuffer, noesis.RPGEODATA_USHORT, idxCount, noesis.RPGEO_TRIANGLE_STRIP)
			elif type ==3:
				rapi.rpgCommitTriangles(finalIdxBuffer, noesis.RPGEODATA_USHORT, idxCount, noesis.RPGEO_TRIANGLE)
			else:
				print("unknown format")
				return 1
		
		bs.seek(start + blockSize)
	print(textureNameList)
	#creating and adding materials
	materials = []
	for matName in materialList:
		material = NoeMaterial(matName, "")
		material.setTexture(matName)
		materials.append(material)
	
	try:
		mdl = rapi.rpgConstructModel()
	except:
		mdl = NoeModel()
	if jointList:
		mdl.setBones(jointList)
	if animList:
		mdl.setAnims(animList)
	if textureList:
		mdl.setModelMaterials(NoeModelMaterials(textureList, materials))
	mdlList.append(mdl)
	
	return mdlList