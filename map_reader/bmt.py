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
class Material:
    name: str
    colors: list[RGB]
    options: bytes
    diffuse: Diffuse


class BMT:
    materials: list[Material]
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
                options = f.read(4)

                diffuse = self.read_diffuse(f)

                material = Material(material_name.decode(), colors, options, diffuse)
                print(material)
                self.materials.append(material)





