
bitfield RGBA { 
    float r;
    float g;
    float b;
    float a;
 } [[sealed, format, color]];

struct Diffuse{
    u32 len;
    char path[len];
    float diffuse_float;
    
    u8 flag_1;
    u8 flag_2;
    bool is_relative;
};

bitfield MaterialOptions {
    bit1: 6;
    tint: 1;
    bit2: 1;
    diffuse: 1;
    alpha: 1;
    unknown: 3;
    bump_map: 1;
    rest: 17;
};

struct Material {

    u32 len;
    char name[len];
    
    RGBA color_0;
    RGBA color_1;
    RGBA color_2;
    RGBA color_3;
    
    float unknown_flag;
    
    MaterialOptions flag;
    
    Diffuse diffuse;
};


struct BMT {
    char header[12];
    
    u32 material_count;
    Material materials[material_count];
};

BMT bmt @ 0;