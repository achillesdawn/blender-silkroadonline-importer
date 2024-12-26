# Plugin Information
bl_info = {
	"name": "Silkroad JMXVNVM",
	"version": (2,1,3),
	"description": ("Import Sikroad Online Navigation Mesh Data"),
	"blender": (2,80,0),
	"category": "Import-Export",
	"author": "JellyBitz",
}

# Import stuffs
import os
import bpy
import re
from bpy.props import StringProperty, BoolProperty, CollectionProperty, FloatProperty
from bpy.types import Operator, OperatorFileListElement
from JellyBMS import BinaryReader, BlenderGetMode, BlenderSetMode

# Import JMXVNVM command
class Import_JMXVNVM(Operator):
	"""Imports a AINavData file from Silkroad Online"""
	bl_idname = "silkroad_import.jmxvnvm_1000" # bpy.ops.silkroad_import.jmxvnvm_1000
	bl_label = "Select .nvm file"
	# Filter only .ban files
	filter_glob: StringProperty(
		default="*.nvm",
		options={'HIDDEN'},
		maxlen=255  # Max internal buffer length, longer would be clamped.
	)
	# Add support to select multiples files
	files: CollectionProperty(
		name="File Path",
		type=OperatorFileListElement
	)
	directory: StringProperty(
		subtype='DIR_PATH'
	)
	# Settings
	setting_scale: FloatProperty(
		name="Scale",
		description="Apply general scale",
		default=0.01,
		min=0.001,
		max=100.0
	)
	setting_region_offset: BoolProperty(
		name="Region Offset",
		description="Keep the worldmap offset position from navmesh",
		default=True,
	)
	setting_data_pk2_path: StringProperty(
		name='Data Path',
		description='Path to the DATA folder from server files',
		default='C:\\Silkroad\\#Server\\Files - Test_In\\Data',
		maxlen=255,
	)
	setting_map_pk2_path: StringProperty(
		name='Map Path',
		description='Path to the MAP folder from server files',
		default='C:\\Silkroad\\#Server\\Files - Test_In\\Map',
		maxlen=255,
	)
	setting_navmesh: BoolProperty(
		name="NavMesh",
		description="Load Navigation Mesh from objects",
		default=False,
	)
	setting_terrain_collision: BoolProperty(
		name="Terrain Collisions",
		description="Load Collisions Mesh from terrain",
		default=False,
	)
	# Class (static) variables
	_objects_ifo_data = {}
	_tile2d_ifo_data = {}
	# Execute command
	def execute(self, Context):
		# Initialize data
		self._objects_ifo_data = {}
		self._tile2d_ifo_data = {}
		# Check all files selected
		for file_elem in self.files:
			if os.path.isfile(os.path.join(self.directory,file_elem.name)):
				self.LoadFile(Context,self.directory,file_elem.name)
		# execution finished
		return {'FINISHED'}
	# Run this as dialog
	def invoke(self, context, event):
		wm = context.window_manager
		wm.fileselect_add(self)
		return {'RUNNING_MODAL'}
	# Drawing dialog
	def draw(self, Context):
		layout = self.layout
		layout.prop(self,'setting_data_pk2_path')
		layout.prop(self,'setting_map_pk2_path')
		layout.prop(self,'setting_scale')
		layout.prop(self,'setting_region_offset')
		layout.prop(self,'setting_navmesh')
		layout.prop(self,'setting_terrain_collision')
	# Loads file to blender
	def LoadFile(self, Context, Path, FileName):
		# Try to read file
		br = None
		filePath = os.path.join(Path,FileName)
		with open(filePath, 'rb') as f:
			br = BinaryReader(f.read())
			# Check file signature
			if br.Length < 12 or br.ReadAscii(12) != "JMXVNVM 1000":
				return False
		if not br:
			return False

		# Try to load file
		data = None
		try:
			# Reset cursor
			br.SeekRead(0)
			data = self.LoadData(br)
		except Exception as ex:
			# Error
			print('Error loading JMXVNVM file:'+FileName+' ['+str(ex)+']')
			return False

		# Import data to blender
		userMode = BlenderGetMode()

		# Process Data
		self.LoadObjectsData()
		self.LoadTile2dData()
		self.ProcessData(Context,data,os.path.splitext(FileName)[0])

		# Get back to normal
		BlenderSetMode(userMode)

		# Success
		print('Loaded:'+filePath)
		return True
	# Loads the data from file structure
	def LoadData(self, br):
		data = {
			'objects':[],
			'cells':[],
			'heightmap_faces':[],
			'heightmap_vertices':[]
		}

		# Skip Signature
		br.SeekRead(12,1)

		# Objects
		count = br.ReadUShort()
		for i in range(count):
			# read object data
			obj = {}
			obj['asset_id'] = br.ReadUInt()

			x,z,y = br.ReadFloat(),br.ReadFloat(),br.ReadFloat()
			obj['local_position'] = [x,y,z]
			obj['type'] = br.ReadUShort()
			obj['yaw'] = br.ReadFloat()
			obj['local_uid'] = br.ReadUShort()

			br.SeekRead(2,1)
			br.SeekRead(1,1)
			obj['is_struct'] = br.ReadByte() == 1
			obj['RID'] = br.ReadUShort()

			# ...
			linkedEdgesCount = br.ReadUShort()
			for j in range(linkedEdgesCount):
				br.SeekRead(2,1)
				br.SeekRead(2,1)
				br.SeekRead(2,1)

			# save object
			data['objects'].append(obj)
		
		# Terrain Mesh - Cells (Quads)
		cellsCount = br.ReadUInt()
		walkableCellsCount = br.ReadUInt()
		for i in range(cellsCount):
			cell = {}
			cell['min'] = [br.ReadFloat(),br.ReadFloat()]
			cell['max'] = [br.ReadFloat(),br.ReadFloat()]
			cell['objects_indices'] = []

			cellObjCount = br.ReadByte()
			for j in range(cellObjCount):
				cell['objects_indices'].append(br.ReadUShort())

			# save cell
			data['cells'].append(cell)

		# Terrain Mesh - Edges Outside Collisions
		count = br.ReadUInt()
		for i in range(count):
			br.SeekRead(8,1)
			br.SeekRead(8,1)

			br.SeekRead(1,1)
			br.SeekRead(1,1)
			br.SeekRead(1,1)

			br.SeekRead(2,1)
			br.SeekRead(2,1)

			br.SeekRead(2,1)
			br.SeekRead(2,1)

		# Terrain Mesh - Edges Inside Collisions
		count = br.ReadUInt()
		for i in range(count):
			br.SeekRead(8,1)
			br.SeekRead(8,1)

			br.SeekRead(1,1)
			br.SeekRead(1,1)
			br.SeekRead(1,1)

			br.SeekRead(2,1)
			br.SeekRead(2,1)

		# TileMap
		heightmap_faces = data['heightmap_faces']
		for i in range(96):
			for j in range(96):
				face = {}
				face['id'] = br.ReadUInt()
				face['flags'] = br.ReadUShort()
				face['tile_id'] = br.ReadUShort()
				heightmap_faces.append(face)

		# Heightmap
		heightmap = data['heightmap_vertices']
		for y in range(97):
			for x in range(97):
				heightmap.append([x*20,y*20,br.ReadFloat()])

		# Return data
		return data

	# Process data from file into Blender
	def ProcessData(self, Context, data, name):
		BlenderSetMode('OBJECT')

		# Collection with everything into the file
		collection = bpy.data.collections.new(name)
		Context.scene.collection.children.link(collection)
		Context.view_layer.active_layer_collection = Context.view_layer.layer_collection.children[collection.name]

		# Create HeightMap object
		mesh = bpy.data.meshes.new("Mesh")
		obj = bpy.data.objects.new(name+'.HeightMap', mesh)
		collection.objects.link(obj)
		Context.view_layer.objects.active = obj # Set active object to work with

		# Apply general scale
		obj.scale = (self.setting_scale,self.setting_scale,self.setting_scale)

		# Region
		region = 0
		match = re.search("([0-9a-zA-Z]{2})([0-9a-zA-Z]{2})$", name)
		if match:
			ry = int(match.group(1),16)
			rx = int(match.group(2),16)
			region = (ry << 8) | rx
			collection.name = name+' (RID:'+str(region)+')'
			# Region offset position
			if self.setting_region_offset:
				obj.location = ((rx - 135) * 1920 * self.setting_scale, (ry - 92) * 1920 * self.setting_scale, 0.0)
		
		# Create Mesh from HeightMap
		w = 97
		h = 97
		heightmap_faces = []
		for i in range(h-1):
			for j in range(w-1):
				a = i*w+j
				b = a+1
				c = a+w
				d = c+1
				heightmap_faces.append([a,b,d,c])
		mesh.from_pydata(data['heightmap_vertices'], [], heightmap_faces)
		# Add default UV Map
		mesh.uv_layers.new(name='UVMap')

		# Set materials from each tile
		if self._tile2d_ifo_data:
			heightmap_faces = data['heightmap_faces']
			for face_idx, heightmap_face in enumerate(heightmap_faces):
				tileData = self._tile2d_ifo_data[heightmap_face['tile_id']]
				tileName = os.path.splitext(tileData['path'])[0]
				# Check material existence by name
				mat = bpy.data.materials.get(tileName)
				if not mat:
					mat = bpy.data.materials.new(name=tileName)
					mat.use_nodes = True
					mat.node_tree.nodes.clear()
					# Set base nodes and link them
					mat.use_nodes = True
					nodes = mat.node_tree.nodes
					output = nodes['ShaderNodeOutputMaterial'] if 'ShaderNodeOutputMaterial' in nodes else mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
					output.name = 'ShaderNodeOutputMaterial'
					output.location = (380,300)
					bsdf = nodes['ShaderNodeBsdfPrincipled'] if 'ShaderNodeBsdfPrincipled' in nodes else mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
					bsdf.name = 'ShaderNodeBsdfPrincipled'
					bsdf.location = (100,300)
					mat.node_tree.links.new(output.inputs['Surface'], bsdf.outputs['BSDF'])					
					# Load texture
					mtrlPath = os.path.join(self.setting_map_pk2_path,'tile2d',tileName+'.dds')
					if not os.path.exists(mtrlPath):
						# Remove header from DDJ
						with open(os.path.join(self.setting_map_pk2_path,'tile2d',tileData['path']), 'rb') as fr:
							fr.seek(20,os.SEEK_SET)
							# Write into DDS
							with open(mtrlPath, 'wb') as fw:
								fw.write(fr.read())
					# Texture node
					texImgNode = nodes.new('ShaderNodeTexImage')
					if os.path.exists(mtrlPath):
						texImgNode.image = bpy.data.images.load(mtrlPath)
					texImgNode.name = tileName
					texImgNode.location = (-185,300)
					# Link texture
					mat.node_tree.links.new(bsdf.inputs['Base Color'], texImgNode.outputs['Color'])
				# Add material to object
				if not obj.data.materials.get(tileName):
					obj.data.materials.append(mat)
				material_index = 0
				for mat_idx, material in enumerate(obj.data.materials):
					if material.name == tileName:
						obj.data.polygons[face_idx].material_index = mat_idx
						break

		# Load objects from navmesh
		for fileObjectData in data['objects']:
			# Make sure this asset has been loaded
			if not fileObjectData['asset_id'] in self._objects_ifo_data:
				continue
			# Avoid duplicated objects
			if fileObjectData['RID'] != region:
				continue
			fileObject = self._objects_ifo_data[fileObjectData['asset_id']]
			# Set values to execute operator
			bpy.ops.silkroad_import.jmxvbms_0110(
				directory=self.setting_data_pk2_path,
				files=[{'name':path} for path in fileObject['mesh_path']],
				setting_navmesh=self.setting_navmesh,
				setting_material_filepath=os.path.join(self.setting_data_pk2_path,fileObject['mtrl_path']),
			)
			# Move meshes to their positions
			for o in Context.selected_objects:
				o.location = (obj.location[0] + fileObjectData['local_position'][0]*self.setting_scale, obj.location[1] + fileObjectData['local_position'][1]*self.setting_scale, fileObjectData['local_position'][2]*self.setting_scale)
				o.rotation_euler[2] = fileObjectData['yaw']
				o.scale = obj.scale
		
		if self.setting_terrain_collision:
			# Deselect all objects
			for o in Context.selected_objects:
				o.select_set(False)
			# Create Collision Mesh
			meshCollision = bpy.data.meshes.new("Mesh")
			objCollision = bpy.data.objects.new(name+'.CollisionMap', meshCollision)
			collection.objects.link(objCollision)
			Context.view_layer.objects.active = objCollision # Set active object to work with
			objCollision.location = obj.location
			objCollision.scale = obj.scale

			# Create Mesh from Collisions
			collisionVertices = []
			collisionFaces = []
			i = 0
			for cell in data['cells']:
				a = [cell['min'][0],cell['min'][1],0.0]
				b = [cell['max'][0],cell['min'][1],0.0]
				c = [cell['max'][0],cell['max'][1],0.0]
				d = [cell['min'][0],cell['max'][1],0.0]
				collisionVertices.append(a)
				collisionVertices.append(b)
				collisionVertices.append(c)
				collisionVertices.append(d)
				collisionFaces.append([i,i+1,i+2,i+3])
				i+=4
			meshCollision.from_pydata(collisionVertices, [], collisionFaces)
			# Remove vertices doubled...
			bpy.ops.object.mode_set(mode='EDIT')
			bpy.ops.mesh.remove_doubles(threshold=0.0001)

	# Load data required from navmesh
	def LoadObjectsData(self):
		# Abort reloading
		if self._objects_ifo_data:
			return
		# Check pk2 path
		if not self.setting_data_pk2_path:
			return
		# Try to load "object.ifo" file
		objects_ifo_path = os.path.join(self.setting_data_pk2_path,'navmesh\\object.ifo')
		if os.path.exists(objects_ifo_path):
			with open(objects_ifo_path,'r',errors='ignore') as f:
				# Read file format
				header = f.readline().rstrip('\n')
				if header == 'JMXVOBJI1000':
					count = int(f.readline().rstrip('\n'))
					for i in range(count):
						objData = f.readline().rstrip('\n').split(' ',2)
						self._objects_ifo_data[int(objData[0])] = {
							'flags':int(objData[1],16),
							'res_path':[objData[2].replace('"','')],
							'mesh_path':[],
							'mtrl_path':''
						}
		# Extract resources from compounds
		for idx in self._objects_ifo_data:
			fileObject = self._objects_ifo_data[idx]
			for i in range(len(fileObject['res_path'])-1,-1,-1):
				res_path = fileObject['res_path'][i]
				object_res_path = os.path.join(self.setting_data_pk2_path,res_path)
				if os.path.exists(object_res_path):
					with open(object_res_path,'rb') as f:
						br = BinaryReader(f.read())
						# Check file signature
						if br.Length < 12 or br.ReadAscii(12) != "JMXVCPD 0101":
							continue
						# Remove this path from resource
						del fileObject['res_path'][i]
						# Read file format
						br.SeekRead(4,1)
						fileOffsetResources = br.ReadUInt()
						# Set cursor at resources
						br.SeekRead(fileOffsetResources)
						resCount = br.ReadUInt()
						for j in range(resCount):
							fileObject['res_path'].append(br.ReadAscii(br.ReadUInt()))
		# Try to load mesh paths from objects
		for idx in self._objects_ifo_data:
			fileObject = self._objects_ifo_data[idx]
			for res_path in fileObject['res_path']:
				object_res_path = os.path.join(self.setting_data_pk2_path,res_path)
				if os.path.exists(object_res_path):
					with open(object_res_path,'rb') as f:
						br = BinaryReader(f.read())
						# Check file signature
						if br.Length < 12 or br.ReadAscii(12) != "JMXVRES 0109":
							continue
						# Read file format
						fileOffsetMtrl = br.ReadUInt()
						fileOffsetMesh = br.ReadUInt()
						br.SeekRead(6*4,1)
						meshFlags = br.ReadUInt()
						# Set cursor at meshes
						br.SeekRead(fileOffsetMesh)
						meshCount = br.ReadUInt()
						for i in range(meshCount):
							meshPath = br.ReadAscii(br.ReadUInt())
							# Make sure it exists
							meshPath = os.path.join(self.setting_data_pk2_path,meshPath)
							if os.path.exists(meshPath):
								fileObject['mesh_path'].append(meshPath)
							# continue reading file format
							if meshFlags & 1:
								br.SeekRead(4,1)
						# Set cursor at mtrl
						br.SeekRead(fileOffsetMtrl)
						mtrlCount = br.ReadUInt()
						for i in range(mtrlCount):
							br.SeekRead(4,1)
							# Set first one only
							fileObject['mtrl_path'] = br.ReadAscii(br.ReadUInt())
							break
	# Load data required from navmesh
	def LoadTile2dData(self):
		# Abort reloading
		if self._tile2d_ifo_data:
			return
		# Check pk2 path
		if not self.setting_map_pk2_path:
			return
		# Try to load "tile2d.ifo" file
		tile2d_ifo_path = os.path.join(self.setting_map_pk2_path,'tile2d.ifo')
		if os.path.exists(tile2d_ifo_path):
			with open(tile2d_ifo_path,'r') as f:
				# Read file format
				header = f.readline().rstrip('\n')
				if header == 'JMXV2DTI1001':
					count = int(f.readline().rstrip('\n'))
					for i in range(count):
						data01 = f.readline().rstrip('\n').split(' ',2)
						data02 = data01[2].split('" "')	
						data03 = data02[1].split('" ')
						grass = None
						if len(data03) > 1:
							grass = data03[1]
						else:
							data03[0] = data03[0][:-1]
						# store data
						self._tile2d_ifo_data[int(data01[0])] = {
							'type':int(data01[1],16),
							'category':data02[0][1:],
							'path':data03[0],
							'grass':grass
						}

# Add dynamic menu into Import
def menu_func_import(self, Context):
	self.layout.operator(Import_JMXVNVM.bl_idname, text="JMXVNVM 1000 (.nvm)")

# Register module
def register():
	bpy.utils.register_class(Import_JMXVNVM)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

# Unregister module
def unregister():
	# unregister backwards to avoid issues
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
	bpy.utils.unregister_class(Import_JMXVNVM)