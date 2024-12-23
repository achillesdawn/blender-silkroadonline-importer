import sys

sys.path.insert(0, "/home/miguel/python/blender_silkroad_importer/map_reader")

import bpy

from bsr import BSRReader
from ofile import MapBlock
from object_list import read_object_list
from bmt import BMT, BMTMaterial
from ddj import DDJTextureReader
from node_tool import NodeTool
from ofile import OReader

from pathlib import Path


DATA_PATH = Path("/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Data")
OBJECT_LIST = Path(
    "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/object.ifo"
)


class BMTImporter(BMT):
    def __init__(self) -> None:
        super().__init__()

    def import_material(self, material: BMTMaterial):
        m = bpy.data.materials.get(material.name)
        if m is not None:
            return

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

        NodeTool.add_nodes(ntree, image)


class MapImporter:
    resources: dict[int, str]
    base_path: Path

    def __init__(self, base_path: Path) -> None:
        assert DATA_PATH.exists()
        assert OBJECT_LIST.exists()
        assert base_path.exists()

        self.base_path = base_path

        self.resources = read_object_list(OBJECT_LIST)
        self.bsr = BSRReader()

    def import_map_blocks_materials(self, map_blocks: list[MapBlock]):
        read_ids: set[int] = set()

        bmt = BMTImporter()

        for map_block in map_blocks:
            for lod in map_block.lods:
                if len(lod) > 0:
                    for ob in lod:
                        if ob.ob_id in read_ids:
                            continue
                        else:
                            read_ids.add(ob.ob_id)

                        resource = self.resources[ob.ob_id]
                        resource_path = DATA_PATH / resource

                        if not resource_path.exists():
                            raise Exception("resource path not found", resource_path)

                        self.bsr.read(resource_path)

                        for material in self.bsr.materials:
                            bmt_path = DATA_PATH / material.name

                            if not bmt_path.exists():
                                raise Exception("not exists", bmt_path)

                            bmt.read(bmt_path)

                            for material in bmt.materials:
                                bmt.import_material(material)

    def read(self):
        o = OReader()
        o.read(self.base_path)

        self.import_map_blocks_materials(o.map_blocks)


if __name__ == "__main__":
    m = MapImporter(
        Path(
            "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/64/68.o"
        )
    )

    m.read()
