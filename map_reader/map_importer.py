import sys

sys.path.insert(0, "/home/miguel/python/blender_silkroad_importer/map_reader")

import bpy
from mathutils import Vector

from bsr import BSRReader, BSRData
from ofile import MapBlock
from object_list import read_object_list
from bmt import BMT, BMTMaterial
from ofile import OReader, O2Reader
from bms import load_bms, import_bms

from ddj import DDJTextureReader
from node_tool import NodeTool

from pathlib import Path


DATA_PATH = Path("/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Data")
OBJECT_LIST = Path(
    "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/object.ifo"
)
MAP_PATH = Path("/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/")


class BMTImporter(BMT):
    def __init__(self) -> None:
        super().__init__()

    def import_material(self, material: BMTMaterial):
        m = bpy.data.materials.get(material.name)
        if m is not None:
            return

        if material.diffuse.is_relative:
            diffuse_path = DATA_PATH / material.diffuse.name
        else:
            diffuse_path = self.path / material.diffuse.name

        if diffuse_path.suffix not in [".dds", ".ddj"]:
            print("unexpected texture path:", diffuse_path.as_posix())
            return

        if not diffuse_path.exists():
            raise Exception("diffuse path does not exist", diffuse_path)

        dds_path = DDJTextureReader.convert_ddj_to_dds(diffuse_path)

        image = bpy.data.images.load(filepath=dds_path.as_posix(), check_existing=True)

        m = bpy.data.materials.new(material.name)
        m.use_nodes = True

        ntree = m.node_tree

        assert ntree

        NodeTool.add_nodes(ntree, image, material.has_alpha)


class BoundingBox:
    def __init__(self, dimensions: Vector, minimum: Vector, maximum: Vector):
        self.dimensions = dimensions
        self.min = minimum
        self.max = maximum

    @classmethod
    def bounding_box(cls, ob: bpy.types.Object):
        bb = [ob.matrix_world @ Vector(vert) for vert in ob.bound_box]

        x = [item.x for item in bb]
        y = [item.y for item in bb]
        z = [item.z for item in bb]

        min_x, min_y, min_z = min(x), min(y), min(z)
        max_x, max_y, max_z = max(x), max(y), max(z)

        dimension_x = abs(max_x - min_x)
        dimension_y = abs(max_y - min_y)
        dimension_z = abs(max_z - min_z)

        data = BoundingBox(
            dimensions=Vector((dimension_x, dimension_y, dimension_z)),
            minimum=Vector((min_x, min_y, min_z)),
            maximum=Vector((max_x, max_y, max_z)),
        )

        return data


def map_range(
    from_range: tuple[float, float], to_range: tuple[float, float], value: float
):
    (a1, a2), (b1, b2) = from_range, to_range
    return b1 + ((value - a1) * (b2 - b1) / (a2 - a1))


class MapImporter:
    resources: dict[int, str]
    base_path: Path

    x_offset: int
    y_offset: int

    imported_materials: set[str]
    bsr_cache: dict[str, BSRData]
    mesh_cache: dict[str, dict]

    def __init__(self) -> None:
        assert DATA_PATH.exists()
        assert OBJECT_LIST.exists()

        self.imported_materials = set()
        self.bsr_cache = {}
        self.mesh_cache = {}

        self.x_offset = 0
        self.y_offset = 0

        self.resources = read_object_list(OBJECT_LIST)
        self.bsr = BSRReader()
        self.bmt = BMTImporter()

    def import_materials(self, data: BSRData):
        for material in data.materials:
            bmt_path = DATA_PATH / material.name

            if bmt_path.as_posix() in self.imported_materials:
                continue

            if not bmt_path.exists():
                raise Exception("not exists", bmt_path)

            self.bmt.read(bmt_path)

            for material in self.bmt.materials:
                self.bmt.import_material(material)

            self.imported_materials.add(bmt_path.as_posix())

    def import_map_blocks_materials(self, map_blocks: list[MapBlock]):
        for map_block in map_blocks:
            for lod in map_block.lods:
                if len(lod) == 0:
                    continue

                for map_ob in lod:
                    print("-" * 12)
                    print(map_ob)

                    resource = self.resources[map_ob.ob_id]
                    resource_path = DATA_PATH / resource

                    data = self.bsr_cache.get(resource_path.as_posix())

                    if data is None:
                        if not resource_path.exists():
                            raise Exception("resource path not found", resource_path)

                        data = self.bsr.read(resource_path)
                        if data is None:
                            continue
                        self.bsr_cache[resource_path.as_posix()] = data

                    self.import_materials(data)

                    if bpy.data.collections.get(f"{self.x_offset}-{self.y_offset}-{map_ob.uid}"):
                        continue

                    obs: list[bpy.types.Object] = []
                    for mesh in data.meshes:
                        mesh_path = DATA_PATH / mesh.name

                        if mesh_path.as_posix() in self.mesh_cache:
                            imported_bms_data = self.mesh_cache[mesh_path.as_posix()]
                        else:
                            if not mesh_path.exists():
                                raise Exception("not exists", mesh_path)

                            imported_bms_data = load_bms(mesh_path)
                            self.mesh_cache[mesh_path.as_posix()] = imported_bms_data

                        imported_ob = import_bms(mesh_path, imported_bms_data)
                        obs.append(imported_ob)

                    for ob in obs:
                        ob.select_set(True)

                    bpy.ops.object.duplicate(linked=True)
                    bpy.ops.object.move_to_collection(
                        collection_index=0,
                        is_new=True,
                        new_collection_name=f"{self.x_offset}-{self.y_offset}-{map_ob.uid}",
                    )

                    collection = bpy.data.collections.get(f"{self.x_offset}-{self.y_offset}-{map_ob.uid}")
                    assert collection

                    x = map_range((0, 2000), (0, 6), map_ob.x)
                    y = map_range((0, 2000), (0, 6), map_ob.z)
                    z = map_range((0, 2000), (0, 6), map_ob.y)

                    location = Vector([x, y, z])

                    offset = Vector(
                        [(self.x_offset * 6) - 0.5, (self.y_offset * 6) - 0.5, 0]
                    )

                    scale = Vector([0.003114, 0.003114, 0.003114])

                    location += offset
                    print("moving to", location)

                    for ob in collection.objects:
                        ob.location = location
                        ob.scale = scale
                        ob.rotation_euler.z = map_ob.yaw

                    bpy.ops.object.select_all(action="DESELECT")

    def read_o(self, path: Path):
        o = OReader()

        self.base_path = path

        self.x_offset = int(path.stem)
        self.y_offset = int(path.parent.stem)

        o.read(self.base_path.with_suffix(".o"))

        self.import_map_blocks_materials(o.map_blocks)

    def read_o2(self, path: Path):
        o = O2Reader()

        self.base_path = path

        self.x_offset = int(path.stem)
        self.y_offset = int(path.parent.stem)

        o.read(self.base_path.with_suffix(".o2"))

        self.import_map_blocks_materials(o.map_blocks)


if __name__ == "__main__":
    m = MapImporter()

    for ob in bpy.data.objects:
        if "x:" in ob.name and "y:" in ob.name:
            x, y = ob.name.split(",")
            x = int(x.split(":")[-1].strip())
            y = int(y.split(":")[-1].strip())

            path = MAP_PATH / f"{y}" / f"{x}"

            m.read_o2(path)
            # m.read_o(path)
