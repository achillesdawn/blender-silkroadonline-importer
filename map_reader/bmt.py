import struct
from pathlib import Path
from dataclasses import dataclass
from io import BufferedReader


@dataclass
class RGB:
    r: float
    g: float
    b: float
    a: float


@dataclass
class Diffuse:
    name: str
    diffuse_float: float
    flag_1: int
    flag_2: int
    is_relative: bool


@dataclass
class BMTMaterial:
    name: str
    colors: list[RGB]

    options: tuple[bool]
    has_alpha: bool
    use_tint: bool
    has_diffuse: bool
    has_bump: bool

    diffuse: Diffuse


class BMT:
    materials: list[BMTMaterial]
    path: Path

    def __init__(self) -> None:
        self.materials = []

    @staticmethod
    def read_diffuse(f: BufferedReader):
        name_len = struct.unpack("<I", f.read(4))[0]
        diffuse_name = f.read(name_len)
        diffuse_float, flag1, flag2, is_relative = struct.unpack(
            "<fBB?", f.read(struct.calcsize("<fBB?"))
        )
        d = Diffuse(diffuse_name.decode(), diffuse_float, flag1, flag2, is_relative)
        return d

    def read(self, path: Path):
        print("[ BMTReader ] reading", path)

        self.path = path.parent

        with open(path, "rb") as f:
            _header = f.read(12)

            print(_header)

            material_count = struct.unpack("<I", f.read(4))[0]

            for _ in range(material_count):
                name_len = struct.unpack("<I", f.read(4))[0]
                material_name = f.read(name_len)

                colors: list[RGB] = []

                for _ in range(4):
                    r, g, b, a = struct.unpack(
                        "<ffff", f.read(struct.calcsize("<ffff"))
                    )
                    colors.append(RGB(r, g, b, a))

                _unknown_flag = struct.unpack("<f", f.read(4))[0]
                options = struct.unpack("<I", f.read(4))[0]

                has_tint: bool = options & 1 << 6 != 0
                has_diffuse: bool = options & 1 << 8 != 0
                has_alpha: bool = options & 1 << 9 != 0
                has_bump: bool = options & 1 << 13 != 0

                diffuse = self.read_diffuse(f)

                material = BMTMaterial(
                    material_name.decode(),
                    colors,
                    options,
                    has_alpha,
                    has_tint,
                    has_diffuse,
                    has_bump,
                    diffuse=diffuse,
                )

                print(material)

                self.materials.append(material)

        print("[ BMTReader ] succesful read")


if __name__ == "__main__":
    b = BMT()
    path = Path(
        "/home/miguel/python/blender_silkroad_importer/Silkroad_DATA-MAP/Data/prim/mtrl/bldg/europe/constantinople/euro_constan_inn01.bmt"
    )
    b.read(path)
