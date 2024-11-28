import bpy
from bpy.types import FloatAttribute, IntAttribute, OperatorFileListElement
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    CollectionProperty,
)
from bpy_extras.io_utils import ImportHelper

import addon_utils

import struct
from dataclasses import dataclass
from pathlib import Path
from io import BufferedReader
from math import floor

from typing import Set, TypedDict, cast

bl_info = {
    "name": "Blender Silkroad Map Importer",
    "author": "https://www.fiverr.com/olivio \n https://github.com/achillesdawn",
    "version": (1, 0, 0),
    "blender": (4, 3, 1),
    "description": "Import SilkRoad Online Maps (.m files) into blender",
    "category": "Import-Export",
}


class Config:
    normal_name = bl_info["name"]
    caps_name = "SILKROAD"
    lower_case_name = caps_name.lower()
    addon_global_var_name = "sro"

    panel_prefix = caps_name + "_PT_"
    operator_prefixz = caps_name + "_OT_"

    path: Path

    @staticmethod
    def get_addon_name():
        addon_path = Path(__file__).resolve().parent.stem
        return addon_path


for mod in addon_utils.modules():  # type: ignore
    if mod.bl_info["name"] == bl_info["name"]:
        filepath = mod.__file__
        Config.path = Path(filepath).parent


FLAG_ENVIRONMENT = "<IH"
FLAG_ENVIRONMENT_SIZE = struct.calcsize(FLAG_ENVIRONMENT)

MAP_VERTEX = "<fHB"
MAP_VERTEX_SIZE = struct.calcsize(MAP_VERTEX)

WATER_DATA = "<BBf"
WATER_DATA_SIZE = struct.calcsize(WATER_DATA)

HEIGHT_DATA = "<ff"
HEIGHT_DATA_SIZE = struct.calcsize(HEIGHT_DATA)


@dataclass
class MapVertex:
    height: float

    #    (MSB)                                                                        (LSB)
    # bit | 15  | 14 | 13 | 12 | 11 | 10 | 09 | 08 | 07 | 06 | 05 | 04 | 03 | 02 | 01 | 00 |
    #     |             Scale            |                   TextureID                     |
    # TextureID corresponds to ID from tile2d.ifo
    texture_data: int

    # lighting direction indicator?
    brightness: int

    def get_texture_data(self):
        texture_id = self.texture_data & 0x3FF
        texture_scale = self.texture_data >> 10

        return texture_id, texture_scale


class MapBlock:
    # 0 = None, 1 = Culled
    flag: int
    # +see "environment.ifo"
    environment_id: int
    # every block has 17 * 17 MapMeshVerticies
    map_vertices: list[MapVertex]

    # -1 = None, 0 = Water, 1 = Ice
    water_type: int
    # See Water folder?
    water_wave_type: int
    water_height: int

    # every block has 16 * 16 MapMeshTiles
    tile_map: list[int]

    # highest point including objects
    height_max: float
    # lowest point including objects
    height_min: float

    def __init__(self, f: BufferedReader) -> None:
        self.flag, self.environment_id = struct.unpack(
            FLAG_ENVIRONMENT, f.read(FLAG_ENVIRONMENT_SIZE)
        )

        self.map_vertices: list[MapVertex] = []
        for _ in range(17 * 17):
            height, texture_data, brightness = struct.unpack(
                MAP_VERTEX, f.read(MAP_VERTEX_SIZE)
            )
            map_vertex = MapVertex(height, texture_data, brightness)
            self.map_vertices.append(map_vertex)

        self.water_type, self.water_wave_type, self.water_height = struct.unpack(
            WATER_DATA, f.read(WATER_DATA_SIZE)
        )

        self.tile_map: list[int] = []
        for _ in range(16 * 16):
            tile = struct.unpack("<H", f.read(2))[0]
            self.tile_map.append(tile)

        self.height_max, self.height_min = struct.unpack(
            HEIGHT_DATA, f.read(HEIGHT_DATA_SIZE)
        )

        _ = f.read(20)


class TextureIndex(TypedDict):
    _id: int
    addr: int
    map_name: str
    file_name: str


class MapImporter:
    texture_map: dict[int, TextureIndex]

    def __init__(self, map_path: Path) -> None:
        self.base_path = map_path

    @staticmethod
    def read_m_file(path: Path) -> list[MapBlock]:
        with open(path, "rb") as f:
            header = f.read(12)
            print(header)

            map_blocks: list[MapBlock] = []
            for _ in range(36):
                map_block = MapBlock(f)
                map_blocks.append(map_block)

            return map_blocks

    def read_tile2d_ifo(self):
        tile2d_ifo_path = self.base_path / "tile2d.ifo"

        if not tile2d_ifo_path.exists():
            raise FileNotFoundError(
                "tile2d.ifo not found! make sure the map_path points to the MAP data folder"
            )

        with open(tile2d_ifo_path, "r") as f:
            lines = f.readlines()

            # header = lines[0]
            # version = lines[1]

            result: dict[int, TextureIndex] = {}

            for line in lines[2:]:
                # format: 00000 0x00000000 "CJfild" "c_dust_fld_01.ddj"
                _id, addr, *rest = line.split(" ")

                if len(rest) == 2:
                    map_name, file_name = rest
                else:
                    rest = " ".join(rest)
                    map_name, file_name = rest.split('" "')
                    if " {" in file_name:
                        file_name = file_name.split(" {")[0]

                _id = int(_id)
                addr = int(addr, 16)
                file_name = file_name.strip().strip('"')

                if not file_name.endswith(".ddj"):
                    print(line)
                    print(file_name)
                    raise ValueError("problem parsing tile2d.ifo")

                value: TextureIndex = {
                    "_id": _id,
                    "addr": addr,
                    "map_name": map_name.strip('"'),
                    "file_name": file_name,
                }

                result[_id] = value

            self.texture_map = result

            return result


class BlenderMapImporter:
    texture_map: dict[int, TextureIndex]
    map_importer: MapImporter

    def __init__(self, map_path: Path) -> None:
        self.base_path = map_path
        self.map_importer = MapImporter(self.base_path)
        self.texture_map = self.map_importer.read_tile2d_ifo()

    def create_image(self, texture_id: int, base_path: Path):
        texture_data = self.texture_map[texture_id]

        texture_path = base_path / texture_data["file_name"]

        image = bpy.data.images.load(texture_path.with_suffix(".dds").as_posix())

        return image

    @staticmethod
    def create_image_node(ntree: bpy.types.ShaderNodeTree, image: bpy.types.Image):
        image_node = cast(
            bpy.types.ShaderNodeTexImage, ntree.nodes.new("ShaderNodeTexImage")
        )
        image_node.image = image
        return image_node

    @staticmethod
    def create_attribute_mix(ntree: bpy.types.ShaderNodeTree, texture_id: int):
        attribute_node = cast(
            bpy.types.ShaderNodeAttribute, ntree.nodes.new("ShaderNodeAttribute")
        )
        attribute_node.attribute_name = f"texture_{texture_id}"

        mix_node = cast(bpy.types.ShaderNodeMix, ntree.nodes.new("ShaderNodeMix"))
        mix_node.data_type = "RGBA"
        mix_node.label = str(texture_id)
        mix_node.name = str(texture_id)

        ntree.links.new(mix_node.inputs[0], attribute_node.outputs[2])
        return attribute_node, mix_node

    def create_material(self, material_name: str, textures: Set[int]):
        material = bpy.data.materials.new(material_name)
        material.use_nodes = True

        base_image_path = self.base_path / "tile2d"

        ntree = material.node_tree
        assert ntree

        previous_mix_node: bpy.types.ShaderNodeMix | None = None

        for idx, texture_id in enumerate(textures):
            image = self.create_image(texture_id, base_image_path)
            image_node = self.create_image_node(ntree, image)
            image_node.location = (idx * 200, idx * 200)

            image_node.name = str(texture_id)
            image_node.label = str(texture_id)

            attribute_node, mix_node = self.create_attribute_mix(ntree, texture_id)
            attribute_node.location = ((idx * 200) - 400, idx * 200)
            mix_node.location = ((idx * 200) + 400, idx * 200)

            ntree.links.new(mix_node.inputs[7], image_node.outputs[0])

            if previous_mix_node:
                ntree.links.new(mix_node.inputs[6], previous_mix_node.outputs[2])
            else:
                mix_node.inputs[6].default_value = (0, 0, 0, 0)  # type: ignore

            previous_mix_node = mix_node

        principled = ntree.nodes["Principled BSDF"]

        assert previous_mix_node
        ntree.links.new(principled.inputs["Base Color"], previous_mix_node.outputs[2])

        principled.inputs[2].default_value = 1  # type: ignore
        return material

    def import_map(self, path: Path):
        assert bpy.context

        map_blocks = self.map_importer.read_m_file(path)

        textures: Set[int] = set()

        for map_block in map_blocks:
            for map_vertex in map_block.map_vertices:
                texture_id, scale = map_vertex.get_texture_data()
                textures.add(texture_id)

        material = self.create_material(path.stem, textures)

        set_height_nodes = bpy.data.node_groups.get("set_height")

        meshes: list[bpy.types.Object] = []

        x_offset = int(path.stem)
        y_offset = int(path.parent.stem)

        print(f"{x_offset=} {y_offset=}")

        for map_block_idx, map_block in enumerate(map_blocks):
            bpy.ops.mesh.primitive_grid_add(  # type: ignore
                x_subdivisions=16,
                y_subdivisions=16,
                size=1,
                enter_editmode=False,
                align="WORLD",
                location=(map_block_idx % 6, floor(map_block_idx / 6), 0),
                scale=(1, 1, 1),
            )

            ob = bpy.context.active_object

            assert ob
            ob.name = path.name
            meshes.append(ob)

            data = cast(bpy.types.Mesh, ob.data)

            data.materials.append(material)  # type: ignore

            data.attributes.new("height", "FLOAT", "POINT")  # type: ignore
            data.attributes.new("scale", "INT", "POINT")  # type: ignore
            data.attributes.new("texture", "INT", "POINT")  # type: ignore
            data.attributes.new("brightness", "INT", "POINT")  # type: ignore

            data.attributes.new("max_height", "FLOAT", "POINT")  # type: ignore
            data.attributes.new("min_height", "FLOAT", "POINT")  # type: ignore

            for texture_id in textures:
                data.attributes.new(f"texture_{texture_id}", "FLOAT", "POINT")  # type: ignore

            height = cast(FloatAttribute, data.attributes["height"])
            scale_attr = cast(IntAttribute, data.attributes["scale"])
            texture = cast(IntAttribute, data.attributes["texture"])
            brightness = cast(IntAttribute, data.attributes["brightness"])

            max_height = cast(FloatAttribute, data.attributes["max_height"])
            min_height = cast(FloatAttribute, data.attributes["min_height"])

            texture_attributes: dict[int, FloatAttribute] = {}
            for texture_id in textures:
                texture_attribute = cast(
                    FloatAttribute, data.attributes[f"texture_{texture_id}"]
                )
                texture_attributes[texture_id] = texture_attribute

            for vertex_idx, map_vertex in enumerate(map_block.map_vertices):
                texture_id, scale = map_vertex.get_texture_data()

                height.data[vertex_idx].value = map_vertex.height
                scale_attr.data[vertex_idx].value = scale
                texture.data[vertex_idx].value = texture_id
                brightness.data[vertex_idx].value = map_vertex.brightness

                max_height.data[vertex_idx].value = map_block.height_max
                min_height.data[vertex_idx].value = map_block.height_min

                texture_attributes[texture_id].data[vertex_idx].value = 1

            data.attributes.new("tile", "INT", "FACE")  # type: ignore

            tile_attr = cast(IntAttribute, data.attributes["tile"])

            for tile_idx, tile in enumerate(map_block.tile_map):
                tile_attr.data[tile_idx].value = tile

            if set_height_nodes:
                geo_nodes = cast(
                    bpy.types.NodesModifier,
                    ob.modifiers.new("Height", "NODES"),  # type: ignore
                )
                geo_nodes.node_group = set_height_nodes
                geo_nodes["Socket_4"] = material
                geo_nodes["Socket_5"] = x_offset
                geo_nodes["Socket_6"] = y_offset

        assert len(meshes) > 0

        for mesh in meshes:
            mesh.select_set(True)

        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        bpy.context.active_object.name = path.name  # type: ignore


class SILKROAD_PROPERTIES(bpy.types.PropertyGroup):
    height_scale: FloatProperty(name="height", default=1)  # type: ignore
    map_data_path: StringProperty(name="map_data_path", subtype="DIR_PATH")  # type: ignore


class BaseClass:
    @staticmethod
    def get_props() -> SILKROAD_PROPERTIES:
        return getattr(bpy.context.scene, Config.addon_global_var_name)  # type: ignore

    @staticmethod
    def get_preferences() -> SILKROAD_PROPERTIES:
        return bpy.context.preferences.addons[Config.get_addon_name()].preferences


class BaseOperator(BaseClass, bpy.types.Operator):
    @staticmethod
    def select_and_make_active(ob: bpy.types.Object):
        for ob_to_deselect in bpy.data.objects:
            if ob_to_deselect == ob:
                continue
            ob_to_deselect.select_set(False)

        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)

        print(f"[ Status ] {ob.name} set to Active Object")


class SILKROAD_OT_IMPORT(BaseOperator, ImportHelper):
    bl_idname = "silkroad.import"
    bl_label = "Import Map"
    bl_description = "Import .m map files"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".m"
    filter_glob: StringProperty(
        default="*.m",
        options={"HIDDEN"},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )  # type: ignore

    files: CollectionProperty(
        name="files",
        type=bpy.types.OperatorFileListElement,  # type: ignore
        options={"HIDDEN", "SKIP_SAVE"},
    )

    directory: StringProperty(subtype="DIR_PATH")  # type: ignore

    @classmethod
    def poll(cls, context: bpy.types.Context | None) -> bool:
        assert context
        enabled_modes = ["OBJECT"]
        return context.mode in enabled_modes

    def append_nodes(self):
        blender_path = "importer.blend"
        path = Config.path / blender_path
        inner_path = "NodeTree"
        nodes_name = "set_height"

        filepath = path / inner_path / nodes_name

        bpy.ops.wm.append(
            filepath=filepath.as_posix(),
            directory=(path / inner_path).as_posix(),
            filename=nodes_name,
        )

    def execute(self, context):
        props = self.get_props()
        paths = [Path(self.directory, file.name) for file in self.files]

        map_data_path = Path(bpy.path.abspath(props.map_data_path))

        b = BlenderMapImporter(map_data_path)

        self.append_nodes()

        for path in paths:
            b.import_map(path)

        return {"FINISHED"}


class SILKROAD_PT_viewportSidePanel(BaseClass, bpy.types.Panel):
    bl_idname = Config.panel_prefix + "viewportSidePanel"
    bl_label = Config.normal_name
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "SRO"

    def draw(self, context):
        layout = self.layout
        props = self.get_props()

        col = layout.column()

        col.label(text="MAP Data Dir", icon="RIGHTARROW_THIN")
        col.prop(props, "map_data_path", text="")

        col.separator()
        col.operator(
            SILKROAD_OT_IMPORT.bl_idname, text="Import Map", icon="NODE_TEXTURE"
        )


classes = [SILKROAD_PROPERTIES, SILKROAD_OT_IMPORT, SILKROAD_PT_viewportSidePanel]


def set_properties():
    setattr(
        bpy.types.Scene,
        Config.addon_global_var_name,
        bpy.props.PointerProperty(
            type=SILKROAD_PROPERTIES,
        ),
    )


def del_properties():
    delattr(bpy.types.Scene, Config.addon_global_var_name)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    set_properties()


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    del_properties()


if __name__ == "__main__":
    register()
