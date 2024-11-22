import struct
from dataclasses import dataclass
from pathlib import Path
from io import BufferedReader




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
        texture_id = self.texture_data & 0x000FFFFF
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


class MapImporter:

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
            raise FileNotFoundError("tile2d.ifo not found! make sure the map_path points to the MAP data folder")
        
        with open(tile2d_ifo_path, 'r') as f:
            lines = f.readlines()

            # header = lines[0]
            # version = lines[1]

            for line in lines[2:]:
                # format: 00000 0x00000000 "CJfild" "c_dust_fld_01.ddj"
                _id, addr, map_name, file_name = line.split(" ")
                print(f"{_id=} {addr=} {map_name=} {file_name=}")
                break
            

map_path = Path("/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Map/")

m = MapImporter(map_path)
# m.read_tile2d_ifo()
map_blocks = m.read_m_file()
