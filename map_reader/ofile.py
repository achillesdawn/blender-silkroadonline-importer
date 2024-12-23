import struct
from pathlib import Path
from io import BufferedReader
from dataclasses import dataclass

from bsr import BSRReader
from read_object_list import read_object_list

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

        print("[ OReader ] reading", filepath)

        with open(filepath, "rb") as f:
            _header = f.read(12)

            for col in range(6):
                for row in range(6):
                    self.read_map_block(f, row, col)

            print("[ OReader ] sucessful read")


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





if __name__ == "__main__":



    o2 = O2Reader()

    test_path = Path(
        "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/64/68.o2"
    )

    o2.read(test_path)
