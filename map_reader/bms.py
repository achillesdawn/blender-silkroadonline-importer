import bpy
import bmesh
from pathlib import Path
import struct

from typing import cast


def get_edge_key(vertex_index_a, vertex_index_b):
    return (
        (str(vertex_index_a) + "," + str(vertex_index_b))
        if (vertex_index_a < vertex_index_b)
        else (str(vertex_index_b) + "," + str(vertex_index_a))
    )


class BinaryReader:
    def __init__(self, Buffer):
        self.buffer = Buffer
        self.length = len(Buffer)
        self.position = 0

    def seek_read(self, Offset, SeekOrigin=0):
        if SeekOrigin == 1:  # Current
            self.position += Offset
        elif SeekOrigin == 2:  # End
            self.position = self.length + Offset
        else:  # Begin
            self.position = Offset

    def read(self, format, size):
        result = struct.unpack_from(format, self.buffer, self.position)[0]
        self.position += size
        return result

    def read_bytes(self, count):
        return self.read("<" + str(count) + "s", count)

    def read_byte(self):
        return self.read("<B", 1)

    def read_s_byte(self):
        return self.read("<b", 1)

    def read_u16(self):
        return self.read("<H", 2)

    def read_i16(self):
        return self.read("<h", 2)

    def read_u32(self):
        return self.read("<I", 4)

    def read_i32(self):
        return self.read("<i", 4)

    def read_float32(self):
        return self.read("<f", 4)

    def read_u64(self):
        return self.read("<q", 8)

    def read_i64(self):
        return self.read("<Q", 8)

    def read_string(self, count, code_page):
        return self.read_bytes(count).decode(code_page)

    def read_ascii(self, count: int):
        return self.read_string(count, "cp1252")


def load_bms(filepath: Path):
    f = open(filepath, "rb")
    br = BinaryReader(f.read())

    # data to be loaded
    data = {
        "name": "",
        "material": "",
        "vertices": [],
        "vertices_uv": [],
        "lightmap_uv": [],
        "lightmap_path": "",
        "vertex_groups": [],
        "faces": [],
        "vertex_clothes": {},
        "edge_clothes": {},
        "cloth_settings": {},
        "bounding_box": {},
        "nav_vertices": [],
        "nav_vertices_normals": [],
        "nav_cells": [],
        "nav_collision_edges": {},
        "nav_events": [],
    }

    # Skip header
    br.seek_read(12, 1)

    # File Offsets (Vertices, Vertex Groups, Faces, Vertex Clothes, Edge Clothes, Bounding Box, OcclusionPortals, NavMesh, Skinned NavMesh, Unknown09)
    br.seek_read(28, 1)
    offsetNavMesh = br.read_u32()
    br.seek_read(4, 1)
    br.seek_read(4, 1)
    br.seek_read(4, 1)
    navFlag = br.read_u32()  # 0 = None, 1 = Edge, 2 = Cell, 4 = Event
    br.seek_read(4, 1)
    vertexFlag = br.read_u32()
    br.seek_read(4, 1)

    # Name & Material
    data["name"] = br.read_ascii(br.read_i32())
    data["material"] = br.read_ascii(br.read_i32())
    br.seek_read(4, 1)

    # File Offset: Vertices
    vertices = data["vertices"]
    vertices_uv = data["vertices_uv"]
    lightmap_uv = data["lightmap_uv"]
    verticesCount = br.read_u32()
    for i in range(verticesCount):
        # Location
        x = br.read_float32()
        z = br.read_float32()
        y = br.read_float32()
        vertices.append([x, y, z])
        # Normal
        br.seek_read(12, 1)
        # UV Location
        u = br.read_float32()
        v = br.read_float32()
        vertices_uv.append([u, 1 - v])
        # Check LightMap
        if vertexFlag & 0x400:
            u = br.read_float32()
            v = br.read_float32()
            lightmap_uv.append([u, 1 - v])
        # Check MorphingData
        if vertexFlag & 0x800:
            br.seek_read(32, 1)
        br.seek_read(12, 1)
    # LightMap Path
    if vertexFlag & 0x400:
        data["lightmap_path"] = br.read_ascii(br.read_u32())
    # ISROR vertex data
    if vertexFlag & 0x1000:
        br.seek_read(br.read_u32() * 24, 1)

    # File Offset: Vertex Groups
    vertexGroups = data["vertex_groups"]
    vertexGroupsCount = br.read_u32()
    if vertexGroupsCount:
        for i in range(vertexGroupsCount):
            name = br.read_ascii(br.read_i32())
            # Add vertex group
            vertexGroups.append({"name": name, "vertex_index": [], "vertex_weight": []})
        for i in range(verticesCount):
            # Weights limit by mesh (2)
            for j in range(2):
                vertexGroupIndex = br.read_byte()
                vertexWeight = br.read_u16()
                if vertexGroupIndex != 0xFF:
                    # Add weight to vertex
                    vg = vertexGroups[vertexGroupIndex]
                    vg["vertex_index"].append(i)
                    vg["vertex_weight"].append(vertexWeight / 0xFFFF)

    # File Offset: Faces
    faces = data["faces"]
    facesCount = br.read_u32()
    for i in range(facesCount):
        # Indices to vertices (triangle mesh)
        a = br.read_u16()
        b = br.read_u16()
        c = br.read_u16()
        # Add face
        faces.append([a, b, c])

    # File Offset: Vertex Clothes
    vertexClothes = data["vertex_clothes"]
    vertexClothesCount = br.read_u32()
    for i in range(vertexClothesCount):
        distance = br.read_float32()
        isPinned = br.read_u32() == 1
        # Add cloth from vertex
        vertexClothes[i] = {"distance": distance, "is_pinned": isPinned}

    # File Offset: Edge Clothes
    edgeClothes = data["edge_clothes"]
    edgeClothesCount = br.read_u32()
    if edgeClothesCount:
        for i in range(edgeClothesCount):
            a = br.read_u32()
            b = br.read_u32()
            distance = br.read_float32()
            # Add it
            edgeClothes[get_edge_key(a, b)] = {
                "vertex_index_a": a,
                "vertex_index_b": b,
                "distance": distance,
            }
        # skip it
        br.seek_read(edgeClothesCount * 4, 1)

        # Cloth simulation parameters
        cloth_settings = data["cloth_settings"]

        cloth_settings["type"] = br.read_u32()
        cloth_settings["offset_x"] = br.read_float32()
        cloth_settings["offset_z"] = br.read_float32()
        cloth_settings["offset_y"] = br.read_float32()
        cloth_settings["speed"] = br.read_float32()
        unkUInt01 = br.read_float32()
        unkUInt02 = br.read_float32()
        cloth_settings["elasticity"] = br.read_float32()
        cloth_settings["movements"] = br.read_i32()

    bbox = data["bounding_box"]
    for i in range(2):
        x = br.read_float32()
        z = br.read_float32()
        y = br.read_float32()
        bbox["min" if i == 0 else "max"] = [x, y, z]

    # hasOcclusionPortal = br.ReadUInt()
    # ...
    # unknown = br.ReadUInt()

    # FileOffset: NavMesh
    if offsetNavMesh:
        br.seek_read(offsetNavMesh)

        navVertices = data["nav_vertices"]
        navVerticesNormals = data["nav_vertices_normals"]
        navVerticesCount = br.read_u32()
        for i in range(navVerticesCount):
            # Add navigation vertex
            x = br.read_float32()
            z = br.read_float32()
            y = br.read_float32()
            navVertices.append([x, y, z])
            # Encoded normals
            normalIndex = br.read_byte()
            navVerticesNormals.append(normalIndex)

        navCells = data["nav_cells"]
        navCellsCount = br.read_u32()
        for i in range(navCellsCount):
            # Add indices to navigation vertices (triangle cell)
            a = br.read_u16()
            b = br.read_u16()
            c = br.read_u16()
            navCells.append([a, b, c])
            # Skip
            br.seek_read(2, 1)
            if navFlag & 2:
                br.seek_read(1, 1)

        navCollisionEdges = data["nav_collision_edges"]
        navCollisionEdgesCount = br.read_u32()
        for i in range(navCollisionEdgesCount):
            a = br.read_u16()
            b = br.read_u16()
            br.seek_read(4, 1)
            flag = br.read_byte()
            # Add Global edge
            navCollisionEdges[get_edge_key(a, b)] = {"is_global": True, "flag": flag}
            # Skip
            if navFlag & 1:
                br.seek_read(1, 1)
        navCollisionEdgesCount = br.read_u32()
        for i in range(navCollisionEdgesCount):
            a = br.read_u16()
            b = br.read_u16()
            br.seek_read(4, 1)
            flag = br.read_byte()
            # Skip
            if navFlag & 1:
                br.seek_read(1, 1)
            # Add Internal edge
            navCollisionEdges[get_edge_key(a, b)] = {"is_global": False, "flag": flag}

        # For display only
        if navFlag & 4:
            navEvents = data["nav_events"]
            eventCount = br.read_u32()
            for i in range(eventCount):
                navEvents.append(br.read_ascii(br.read_u32()))

        # GlobalLookupGrid stuffs
        br.seek_read(8, 1)
        width = br.read_u32()
        height = br.read_u32()
        br.seek_read(4, 1)
        for h in range(height):
            for w in range(width):
                count = br.read_u32()
                lst = []
                for c in range(count):
                    lst.append(br.read_u16())

    f.close()

    return data



def import_bms(path: Path, data):
    
    context = cast(bpy.types.Context, bpy.context)
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    if bpy.data.objects.get(data["name"]):
        return cast(bpy.types.Object, bpy.data.objects[data["name"]])
    
    imported_collection = bpy.data.collections.get("bms_import")
    if imported_collection is None:
        imported_collection = bpy.data.collections.new("bms_import")
        context.collection.children.link(imported_collection)


    mesh = bpy.data.meshes.new("Mesh")
    ob = bpy.data.objects.new(data["name"], mesh)

    imported_collection.objects.link(ob)

    ob.select_set(True)
    context.view_layer.objects.active = ob

    ob_data = cast(bpy.types.Mesh, ob.data)

    faces = data["faces"]
    mesh.from_pydata(data["vertices"], [], faces)

    vertex_groups = data["vertex_groups"]
    for vg in vertex_groups:
        group = ob.vertex_groups.new(name=vg["name"])
        group.add(vg["vertex_index"], 1, "ADD")

    # Set weight from vertices
    for vert in ob_data.vertices:
        for g in vert.groups:
            vg = vertex_groups[g.group]
            for i, index in enumerate(vg["vertex_index"]):
                if vert.index == index:
                    g.weight = vg["vertex_weight"][i]

    # Add Texture Map
    vertices_uv = data["vertices_uv"]
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for i, face in enumerate(mesh.polygons):
        for j, loopindex in enumerate(face.loop_indices):
            # Select the face
            f = faces[i]
            # Select the vertex index
            uv = vertices_uv[f[j]]
            # Set UV values
            uv_layer.data[loopindex].uv = uv

    # Add Lightmap if exists
    lightmap_uv = data["lightmap_uv"]
    if lightmap_uv:
        uv_layer = mesh.uv_layers.new(name="LightMap")
        for i, face in enumerate(mesh.polygons):
            for j, loopindex in enumerate(face.loop_indices):
                # Select the face
                f = faces[i]
                # Select the vertex index
                uv = lightmap_uv[f[j]]
                # Set UV values
                uv_layer.data[loopindex].uv = uv

    
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(mesh)

    # Add Cloth from vertices
    vertex_clothes = data["vertex_clothes"]
    vertex_clothes_layer = bm.verts.layers.float.new("vertex_clothes")
    if vertex_clothes:
        for vert in bm.verts:
            # Set vertex info
            vert[vertex_clothes_layer] = (
                vertex_clothes[vert.index]["distance"]
                if vert.index in vertex_clothes
                else 0.0
            )

    # Add Cloth from edges
    edge_clothes = data["edge_clothes"]
    edge_clothes_layer = bm.edges.layers.float.new("edge_clothes")
    if edge_clothes:
        for e in bm.edges:
            # Get edge
            a = e.verts[0].index
            b = e.verts[1].index
            edgeKey = get_edge_key(a, b)
            # Set edge info
            e[edge_clothes_layer] = (
                edge_clothes[edgeKey]["distance"] if edgeKey in edge_clothes else 0.0
            )
        # Save property - cloth settings
        mesh["SilkroadOnline_ClothSettings"] = data["cloth_settings"]

    bpy.ops.object.mode_set(mode="OBJECT")
    
    mat = bpy.data.materials.get(data["material"])
    if not mat:
        raise Exception("material not found")

    if ob_data.materials:
        ob_data.materials[0] = mat
    else:
        ob_data.materials.append(mat)

    return ob


#     if os.path.exists(self.setting_material_filepath):
#         with open(self.setting_material_filepath, "rb") as f:
#             br = BinaryReader(f.read())
#             # Check file signature
#             if br.length > 12 and br.read_ascii(12) == "JMXVBMT 0102":
#                 mtrlCount = br.read_u32()
#                 for i in range(mtrlCount):
#                     mtrlName = br.read_ascii(br.read_u32())
#                     br.seek_read(16 * 4, 1)
#                     br.seek_read(4, 1)
#                     mtrlFlag = br.read_u32()
#                     mtrlPath = br.read_ascii(br.read_u32())
#                     br.seek_read(4, 1)
#                     br.seek_read(2, 1)
#                     isRelativeToData = br.read_byte() == 1
#                     # iSRO file using NormalMap
#                     if mtrlFlag & 0x2000:
#                         br.seek_read(br.read_u32(), 1)
#                         br.seek_read(4, 1)
#                     # Set material path to be used
#                     if data["material"] == mtrlName:
#                         # Check if path is relative to data root
#                         if isRelativeToData:
#                             dataRootIndex = (
#                                 self.setting_material_filepath.lower().index(
#                                     "\\data\\prim\\"
#                                 )
#                             )
#                             if dataRootIndex != -1:
#                                 mtrlPath = os.path.join(
#                                     self.setting_material_filepath[
#                                         : dataRootIndex + 5
#                                     ],
#                                     mtrlPath,
#                                 )
#                                 # keep path safe
#                                 if os.path.exists(mtrlPath):
#                                     data["material_filepath"] = mtrlPath
#                         else:
#                             mtrlPath = os.path.join(
#                                 os.path.dirname(self.setting_material_filepath),
#                                 mtrlPath,
#                             )
#                             # keep path safe
#                             if os.path.exists(mtrlPath):
#                                 data["material_filepath"] = mtrlPath
# # Try to find texture name at the same folder
#     if not data["material_filepath"]:
#         mtrlExtensions = ["dds", "png", "jpg", "tga", "jpeg", "ddj"]
#         for ext in mtrlExtensions:
#             mtrlPath = os.path.join(path: Path, data["material"] + "." + ext)
#             if os.path.exists(mtrlPath):
#                 data["material_filepath"] = mtrlPath
#                 break
#     # Convert DDJ to DDS
#     if data["material_filepath"] and data["material_filepath"].endswith(".ddj"):
#         mtrlPath = os.path.splitext(data["material_filepath"])[0] + ".dds"
#         if not os.path.exists(mtrlPath):
#             # Remove header from DDJ
#             with open(data["material_filepath"], "rb") as fr:
#                 fr.seek(20, os.SEEK_SET)
#                 # Write into DDS
#                 with open(mtrlPath, "wb") as fw:
#                     fw.write(fr.read())
#         data["material_filepath"] = mtrlPath
#     # Load texture
#     if data["material_filepath"]:
#         pathHash = str(hash(data["material_filepath"]))
#         if pathHash in nodes:
#             texImgNode = nodes[pathHash]
#         else:
#             # Calculate position by checking the nodes on with the same column
#             xloc = -185
#             yloc = 0
#             for n in nodes:
#                 if (
#                     n.type == "TEX_IMAGE"
#                     and n.location[0] == xloc
#                     and n.location[1] <= yloc
#                 ):
#                     yloc = n.location[1] - 290  # fixed node height
#             # Create node
#             texImgNode = nodes.new("ShaderNodeTexImage")
#             texImgNode.name = pathHash
#             texImgNode.location = (xloc, yloc)
#         # Try to load image if doesn't have one yet
#         if not (texImgNode.image and texImgNode.image.has_data):
#             try:
#                 texImgNode.image = bpy.data.images.load(data["material_filepath"])
#             except:
#                 pass
#         # Link texture
#         mat.node_tree.links.new(bsdf.inputs["Base Color"], texImgNode.outputs["Color"])

#     # Create BBOX
#     if self.setting_bounding_box:
#         # Make sure bbox has right values to use
#         values = data["bounding_box"]["min"] + data["bounding_box"]["max"]
#         createBBox = True
#         for value in values:
#             if math.isnan(value):
#                 createBBox = False
#                 break
#         if createBBox:
#             # Create object
#             mesh = bpy.data.meshes.new("Mesh")
#             objBBox = bpy.data.objects.new(data["name"] + ".BoundingBox", mesh)
#             context.collection.objects.link(objBBox)
#             objBBox.select_set(True)
#             # Create mesh
#             bboxVertices = [
#                 [values[0], values[1], values[2]],
#                 [values[3], values[1], values[2]],
#                 [values[0], values[4], values[2]],
#                 [values[3], values[4], values[2]],
#                 [values[0], values[1], values[5]],
#                 [values[3], values[1], values[5]],
#                 [values[0], values[4], values[5]],
#                 [values[3], values[4], values[5]],
#             ]
#             bboxEdges = [
#                 [0, 1],
#                 [0, 2],
#                 [1, 3],
#                 [2, 3],
#                 [0, 4],
#                 [1, 5],
#                 [2, 6],
#                 [3, 7],
#                 [4, 5],
#                 [4, 6],
#                 [5, 7],
#                 [6, 7],
#             ]
#             mesh.from_pydata(bboxVertices, bboxEdges, [])

#     # Check NavMesh data
#     if self.setting_navmesh and data["nav_vertices"]:
#         # Create object
#         mesh = bpy.data.meshes.new("Mesh")
#         objNav = bpy.data.objects.new(ob.name + ".NavMesh", mesh)
#         context.collection.objects.link(objNav)
#         objNav.select_set(True)
#         # Create mesh
#         mesh.from_pydata(data["nav_vertices"], [], data["nav_cells"])

#         # Create layers which contains collisions
#         blender_set_mode("EDIT")
#         bm = bmesh.from_edit_mesh(mesh)

#         # Add collision data from edges
#         navCollisionEdges = data["nav_collision_edges"]
#         navEdgesOptionsLayer = bm.edges.layers.int.new("nav_edges_options")

#         # Global & Internal
#         if navCollisionEdges:
#             for e in bm.edges:
#                 # Get edge
#                 a = e.verts[0].index
#                 b = e.verts[1].index
#                 edgeData = navCollisionEdges[get_edge_key(a, b)]
#                 # Set flags data
#                 e[navEdgesOptionsLayer] = edgeData["flag"]
#         # Save property - NavMesh Events
#         mesh["SilkroadOnline_NavMeshEvents"] = data["nav_events"]


if __name__ == "__main__":
    path = Path(
        "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Data/prim/mesh/nature/asia minor/tree/asiaminor_tree01_1.bms"
    )
    data = load_bms(path)

    print(data)

    import_bms(path, data)
