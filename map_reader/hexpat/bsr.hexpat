struct BSR {
    char header[12];
    
    u32 pointer_material;
    u32 pointer_mesh;
    u32 pointer_skeleton;
    u32 pointer_animation;
    u32 pointer_mesh_group;
    u32 pointer_animation_group;
    u32 pointer_palette;
    u32 pointer_bbox;
    
    u32 is_prim_mesh;
    u32 is_mod_data;
    u32 flag2;
    u32 flag3;
    u32 flag4;
    
    u32 res_type;
    u32 name_len;
    char name[name_len];
    
    u32 something;
    u32 res_name;
    char unknown_buffer[40];
};

struct Material {
    u32 material_id;
    u32 material_len;
    char material_path[material_len];
};

struct Materials {
    u32 material_set_count;
    Material materials[material_set_count];
};

struct Mesh {
    u32 mesh_path_len;
    char mesh_path[mesh_path_len];
    u32 flag;
    
};

struct Meshes {
    u32 mesh_count;
    Mesh meshes[mesh_count];
};

struct MeshGroup {
    u32 len;
    char group_name[len];
};

struct MeshGroups {
    u32 mesh_group_count;
    MeshGroup group[mesh_group_count];
};

struct Bbox {
    u32 len;
    char root_mesh[len];
    float bbox[6];
    float bbx_limits[6];
    u32 has_extra_data;
    
    if (has_extra_data == 1) {
        u8 extra_data[64];
    }
};

BSR bsr @0;

Bbox bbox @ bsr.pointer_bbox;
Materials materials @ bsr.pointer_material;
Meshes meshes @ bsr.pointer_mesh;
MeshGroups mesh_groups @ bsr.pointer_mesh_group;