import struct
from pathlib import Path
from io import BufferedReader
from dataclasses import dataclass

from bsr import BSRReader

OBJ_ID = "<I"
VECTOR_3 = "<fff"


DATA_PATH = Path("/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Data")


@dataclass
class MapObject:
    ob_id: int
    x: float
    y: float
    z: float
    is_static: bool
    yaw: float
    uid: int
    short: int
    is_big: bool
    is_struct: bool
    region_id: int | None


class MapBlock:
    lods: list[list[MapObject]]

    def __init__(self, x: int, y: int) -> None:
        self.lods = []
        self.x = x
        self.y = y


class OReader:
    map_blocks: list[MapBlock]

    def __init__(self) -> None:
        self.map_blocks = []

    @staticmethod
    def read_struct(f: BufferedReader, struct_type: str):
        return struct.unpack(struct_type, f.read(struct.calcsize(struct_type)))

    def read_map_block(self, f: BufferedReader, row: int, col: int):
        m = MapBlock(row, col)

        for _ in range(4):
            ob_count: int = self.read_struct(f, "H")[0]
            # print(f"{lod_num=}  {ob_count=}")

            lod: list[MapObject] = []

            for _ in range(ob_count):
                obj_id = self.read_struct(f, OBJ_ID)[0]
                location_x, location_y, location_z = self.read_struct(f, VECTOR_3)
                is_static, yaw, uid, short, is_big, is_struct = self.read_struct(
                    f, "<HfHH??"
                )

                map_object = MapObject(
                    obj_id,
                    location_x,
                    location_y,
                    location_z,
                    is_static,
                    yaw,
                    uid,
                    short,
                    is_big,
                    is_struct,
                    None,
                )

                lod.append(map_object)

            m.lods.append(lod)

        self.map_blocks.append(m)

    def read(self, filepath: Path):
        with open(filepath, "rb") as f:
            _header = f.read(12)

            for col in range(6):
                for row in range(6):
                    self.read_map_block(f, row, col)

            print("DONE")


class O2Reader(OReader):
    def __init__(self) -> None:
        super().__init__()

    def read_map_block(self, f: BufferedReader, row: int, col: int):
        m = MapBlock(row, col)

        for _ in range(4):
            ob_count: int = self.read_struct(f, "H")[0]
            # print(f"{lod_num=}  {ob_count=}")

            lod: list[MapObject] = []

            for _ in range(ob_count):
                obj_id = self.read_struct(f, OBJ_ID)[0]
                location_x, location_y, location_z = self.read_struct(f, VECTOR_3)
                is_static, yaw, uid, short, is_big, is_struct, region_id = (
                    self.read_struct(f, "<HfHH??H")
                )

                map_object = MapObject(
                    obj_id,
                    location_x,
                    location_y,
                    location_z,
                    is_static,
                    yaw,
                    uid,
                    short,
                    is_big,
                    is_struct,
                    region_id,
                )

                lod.append(map_object)

            m.lods.append(lod)

        self.map_blocks.append(m)


def read_object_list(path: Path) -> dict[int, str]:
    resources: dict[int, str] = {}

    with open(path, "rb") as f:
        lines = f.readlines()

    header = lines[0]
    num_objects = lines[1]

    print(header, num_objects)

    for line in lines[2:]:
        res_id, rest = line.split(b" ", 1)
        name = rest.split(b" ", 1)[-1]

        resources[int(res_id)] = (
            name.decode("latin-1").strip().strip('"').replace("\\", "/")
        )

    return resources



if __name__ == "__main__":
    resources = read_object_list(
        path=Path(
            "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/object.ifo"
        )
    )

    o = OReader()

    test_path = Path(
        "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/64/68.o"
    )

    bsr = BSRReader()

    o.read(test_path)
    for map_block in o.map_blocks:
        for lod in map_block.lods:
            if len(lod) > 0:
                for ob in lod:
                    resource = resources[ob.ob_id]
                    resource_path = DATA_PATH / resource

                    if not resource_path.exists():
                        raise Exception("resource path not found", resource_path)

                    bsr.read(resource_path)

                    for material in bsr.materials:
                        print(material)

    # o2 = O2Reader()

    # test_path = Path(
    #     "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/64/68.o2"
    # )

    # o2.read(test_path)
